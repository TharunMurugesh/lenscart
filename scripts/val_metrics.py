"""Full validation metrics for the selected model (same columns as test_metrics.csv).

Uses the VAL split only, so it can be run any number of times. Writes results/val_metrics.csv.

Run: python scripts/val_metrics.py --name m1
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (HEADS, RESULTS, RUNS, LensNet, eval_transform, head_sizes,  # noqa: E402
                    load_split, make_loader, predict)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="m1")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    run = RUNS / args.name
    info = json.loads((run / "run.json").read_text(encoding="utf-8"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ck = torch.load(run / "best.pt", map_location=device, weights_only=False)
    model = LensNet(info["backbone"], head_sizes(), pretrained=False).to(device)
    model.load_state_dict(ck["model"])

    split = load_split(final=True)
    val = split[split["split"] == "val"].reset_index(drop=True)
    pred = predict(model, make_loader(val, eval_transform(), 128, workers=args.workers), device)
    Y = pred["labels"]

    rows = []
    for j, h in enumerate(HEADS):
        logits = pred["logits"][h]
        m = Y[:, j] >= 0
        yt, yp = Y[m, j], logits[m].argmax(1)
        p, r, f, _ = precision_recall_fscore_support(yt, yp, average="macro", zero_division=0)
        top3 = np.nan
        if h in ("articleType", "baseColour"):
            top3 = float((np.argsort(-logits[m], 1)[:, :3] == yt[:, None]).any(1).mean())
        rows.append({"head": h, "n": int(m.sum()), "accuracy": accuracy_score(yt, yp),
                     "macro_precision": p, "macro_recall": r, "macro_f1": f,
                     "weighted_f1": f1_score(yt, yp, average="weighted", zero_division=0),
                     "top3_accuracy": top3, "epoch": int(ck["epoch"])})
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / "val_metrics.csv", index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
