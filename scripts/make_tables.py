"""Collect val results of the variant runs into paper Tables IV and V (handoff section 8).

Each row uses the run's best epoch (by val score). Runs that have not finished are listed
as "not run" with empty numbers, never estimated.

Run: python scripts/make_tables.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HEADS, RESULTS, RUNS  # noqa: E402

TABLE4 = [("IV-a", "iv_a", "Frozen backbone only (Stage A, 6 epochs)"),
          ("IV-b", "iv_b", "Full settings (short schedule)"),
          ("IV-c", "iv_c", "No class weights"),
          ("IV-d", "iv_d", "No augmentation"),
          ("IV-e", "iv_e", "Background replaced by real photos (p=0.5)")]
TABLE5 = [("V-a", "iv_b", "EfficientNet-B0 (= IV-b)"),
          ("V-b", "v_b", "ResNet50"),
          ("V-c", "clip/v_c.json", "FashionCLIP linear probe"),
          ("V-d", "clip/v_d.json", "FashionCLIP zero-shot (M6)")]


def load(ref: str):
    if ref.endswith(".json"):
        p = RUNS / ref
        if not p.exists():
            return None
        d = json.loads(p.read_text(encoding="utf-8"))
        return {**{k: d[k] for k in d if k.startswith("val_")}, "train_seconds": d["train_seconds"],
                "best_epoch": "", "epochs_run": "", "batch": ""}
    p = RUNS / ref / "run.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return {**{k: v for k, v in d["best"].items() if k.startswith("val_")},
            "train_seconds": d["train_seconds"], "best_epoch": d["best_epoch"],
            "epochs_run": d["epochs_run"], "batch": d["batch"]}


def build(spec, label):
    rows = []
    for run, ref, desc in spec:
        r = load(ref)
        row = {"run": run, label: desc}
        if r is None:
            row["status"] = "not run"
        else:
            row["status"] = "done"
            for h in HEADS:
                row[f"val_macro_f1_{h}"] = r[f"val_f1_{h}"]
            row["val_macro_f1_mean"] = r["val_score"]
            for k in ("best_epoch", "epochs_run", "batch", "train_seconds"):
                row[k] = r[k]
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    t4 = build(TABLE4, "change")
    t5 = build(TABLE5, "model")
    t4.to_csv(RESULTS / "table4_ablation.csv", index=False)
    t5.to_csv(RESULTS / "table5_backbones.csv", index=False)
    print(t4.to_string(index=False))
    print(t5.to_string(index=False))


if __name__ == "__main__":
    main()
