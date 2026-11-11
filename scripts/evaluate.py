"""Final test evaluation of the main model (handoff section 7). Run ONCE, after all training.

Reads runs/<name>/best.pt and prepared/split_final.csv (test rows). Writes to results/:
  test_metrics.csv, test_ci.csv, per_class_<head>.csv, cm_<head>.png, top_confusions.csv,
  curves.png, history.csv, audit.csv, test_predictions.csv

Refuses to run if results/test_metrics.csv already exists (the test set is used once).

Run: python scripts/evaluate.py --name m1
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_recall_fscore_support)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (HEADS, RESULTS, RUNS, SEED, LensNet, class_names, eval_transform,  # noqa: E402
                    head_sizes, load_split, make_loader, predict)

N_BOOT = 1000
MIN_GROUP = 30


def softmax(z):
    z = z - z.max(1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(1, keepdims=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="m1")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    RESULTS.mkdir(exist_ok=True)
    if (RESULTS / "test_metrics.csv").exists():
        sys.exit("results/test_metrics.csv exists: the test set has already been evaluated.")

    run = RUNS / args.name
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ck = torch.load(run / "best.pt", map_location=device, weights_only=False)
    bb = json.loads((run / "run.json").read_text())["backbone"]
    model = LensNet(bb, head_sizes(), pretrained=False).to(device)
    model.load_state_dict(ck["model"])
    print(f"loaded {run / 'best.pt'} (epoch {ck['epoch']})")

    split = load_split(final=True)
    test = split[split["split"] == "test"].reset_index(drop=True)
    pred = predict(model, make_loader(test, eval_transform(), 128, workers=args.workers), device)
    Y = pred["labels"]

    metrics, ci_rows, preds_out = [], [], {"id": test["id"]}
    rng = np.random.default_rng(SEED)
    for j, h in enumerate(HEADS):
        names = class_names(h)
        logits = pred["logits"][h]
        prob = softmax(logits)
        yp_all = logits.argmax(1)
        m = Y[:, j] >= 0
        yt, yp = Y[m, j], yp_all[m]

        p, r, f, _ = precision_recall_fscore_support(yt, yp, average="macro", zero_division=0)
        row = {"head": h, "n": int(m.sum()), "accuracy": accuracy_score(yt, yp),
               "macro_precision": p, "macro_recall": r, "macro_f1": f,
               "weighted_f1": f1_score(yt, yp, average="weighted", zero_division=0)}
        if h in ("articleType", "baseColour"):
            top3 = np.argsort(-logits[m], 1)[:, :3]
            row["top3_accuracy"] = float((top3 == yt[:, None]).any(1).mean())
        else:
            row["top3_accuracy"] = np.nan
        metrics.append(row)

        # bootstrap CIs
        accs, f1s = np.empty(N_BOOT), np.empty(N_BOOT)
        for b in range(N_BOOT):
            idx = rng.integers(0, len(yt), len(yt))
            accs[b] = (yt[idx] == yp[idx]).mean()
            f1s[b] = f1_score(yt[idx], yp[idx], average="macro", zero_division=0)
        for metric, vals, point in (("accuracy", accs, row["accuracy"]),
                                    ("macro_f1", f1s, row["macro_f1"])):
            lo, hi = np.percentile(vals, [2.5, 97.5])
            ci_rows.append({"head": h, "metric": metric, "value": point,
                            "ci95_low": lo, "ci95_high": hi, "resamples": N_BOOT})

        # per class
        labels = list(range(len(names)))
        p, r, f, s = precision_recall_fscore_support(yt, yp, labels=labels, zero_division=0)
        pd.DataFrame({"class": names, "precision": p, "recall": r, "f1": f, "support": s}) \
            .to_csv(RESULTS / f"per_class_{h}.csv", index=False)

        # confusion matrix, row-normalised
        cm = confusion_matrix(yt, yp, labels=labels)
        cmn = cm / np.maximum(cm.sum(1, keepdims=True), 1)
        k = len(names)
        fig, ax = plt.subplots(figsize=(max(5, 0.32 * k + 2), max(4, 0.32 * k + 1.5)))
        im = ax.imshow(cmn, cmap="Blues", vmin=0, vmax=1)
        ax.set_xticks(labels, names, rotation=90, fontsize=7 if k > 20 else 9)
        ax.set_yticks(labels, names, fontsize=7 if k > 20 else 9)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        ax.set_title(f"{h}: confusion matrix (row-normalised, test)")
        if k <= 20:
            for a in range(k):
                for c in range(k):
                    if cmn[a, c] >= 0.01:
                        ax.text(c, a, f"{cmn[a, c]:.2f}", ha="center", va="center", fontsize=7,
                                color="white" if cmn[a, c] > 0.5 else "black")
        fig.colorbar(im, ax=ax, fraction=0.046)
        fig.tight_layout()
        fig.savefig(RESULTS / f"cm_{h}.png", dpi=150)
        plt.close(fig)

        if h == "articleType":
            off = [(names[a], names[c], int(cm[a, c])) for a in range(k) for c in range(k)
                   if a != c and cm[a, c] > 0]
            off.sort(key=lambda t: -t[2])
            pd.DataFrame(off[:15], columns=["true", "predicted", "count"]) \
                .to_csv(RESULTS / "top_confusions.csv", index=False)

        preds_out[f"true_{h}"] = [names[v] if v >= 0 else "" for v in Y[:, j]]
        preds_out[f"pred_{h}"] = [names[v] for v in yp_all]
        preds_out[f"conf_{h}"] = prob.max(1).round(4)

    pd.DataFrame(metrics).to_csv(RESULTS / "test_metrics.csv", index=False)
    pd.DataFrame(ci_rows).to_csv(RESULTS / "test_ci.csv", index=False)
    pd.DataFrame(preds_out).to_csv(RESULTS / "test_predictions.csv", index=False)

    # audit: articleType by gender and by masterCategory
    yt_a, yp_a = Y[:, 0], pred["logits"]["articleType"].argmax(1)
    audit = []
    for col in ("gender", "masterCategory"):
        for g, idx in test.groupby(col).groups.items():
            idx = np.asarray(idx)
            n = len(idx)
            ok = n >= MIN_GROUP
            audit.append({"group_by": col, "group": g, "n": n,
                          "accuracy": accuracy_score(yt_a[idx], yp_a[idx]) if ok else "N/A",
                          "macro_f1": f1_score(yt_a[idx], yp_a[idx], average="macro",
                                               zero_division=0) if ok else "N/A"})
    pd.DataFrame(audit).to_csv(RESULTS / "audit.csv", index=False)

    # training curves
    hist = pd.read_csv(run / "history.csv")
    shutil.copy(run / "history.csv", RESULTS / "history.csv")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    a1.plot(hist["epoch"], hist["train_loss"], "o-", label="train")
    a1.plot(hist["epoch"], hist["val_loss"], "o-", label="val")
    a1.set_xlabel("Epoch")
    a1.set_ylabel("Loss (sum of 4 heads)")
    a1.legend()
    for h in HEADS:
        a2.plot(hist["epoch"], hist[f"val_f1_{h}"], "o-", label=h)
    a2.plot(hist["epoch"], hist["val_score"], "k--", label="mean (val score)")
    a2.set_xlabel("Epoch")
    a2.set_ylabel("Val macro F1")
    a2.legend(fontsize=8)
    b_start = hist.loc[hist["stage"] == "B", "epoch"].min()
    if pd.notna(b_start):
        for a in (a1, a2):
            a.axvline(b_start - 0.5, color="grey", lw=0.8, ls=":")
    fig.tight_layout()
    fig.savefig(RESULTS / "curves.png", dpi=150)
    plt.close(fig)

    print(pd.DataFrame(metrics).to_string(index=False))


if __name__ == "__main__":
    main()
