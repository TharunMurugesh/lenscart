"""Package the real training results for the website's "Our AI model" page.

Reads results/ and prepared/ (all produced by the training run) and writes:
  site/data/model_report.json   every number shown on the page (nothing is typed by hand)
  site/img/model/*.png          training curves, confusion matrices, class distribution
  site/img/test/<id>.jpg        a fixed random sample of TEST images for the live Test mode

Run: python scripts/build_model_report.py
"""

import json
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RES, PREP, SITE = ROOT / "results", ROOT / "prepared", ROOT / "site"
RESIZED = ROOT / "data" / "resized"
HEADS = ["articleType", "baseColour", "gender", "usage"]
TEST_SAMPLE = 240
SEED = 42


def records(path: Path) -> list:
    df = pd.read_csv(path)
    return json.loads(df.to_json(orient="records"))


def main() -> None:
    (SITE / "data").mkdir(parents=True, exist_ok=True)
    img_model, img_test = SITE / "img" / "model", SITE / "img" / "test"
    img_model.mkdir(parents=True, exist_ok=True)
    img_test.mkdir(parents=True, exist_ok=True)

    for name in ["curves.png", "cm_articleType.png", "cm_baseColour.png", "cm_gender.png", "cm_usage.png"]:
        shutil.copy2(RES / name, img_model / name)
    shutil.copy2(PREP / "fig1_article_types.png", img_model / "fig1_article_types.png")

    stats = json.loads((RES / "preprocess_stats.json").read_text(encoding="utf-8"))
    history = pd.read_csv(RES / "history.csv")
    maps = json.loads((PREP / "label_maps.json").read_text(encoding="utf-8"))

    preds = pd.read_csv(RES / "test_predictions.csv")
    sample = preds.sample(n=min(TEST_SAMPLE, len(preds)), random_state=SEED)
    test_items = []
    for row in sample.itertuples(index=False):
        src = RESIZED / f"{row.id}.jpg"
        if not src.exists():
            continue
        shutil.copy2(src, img_test / f"{row.id}.jpg")
        item = {"id": int(row.id), "image": f"img/test/{row.id}.jpg"}
        for h in HEADS:
            t = getattr(row, f"true_{h}")
            item[h] = {"true": None if pd.isna(t) else t, "pred": getattr(row, f"pred_{h}"),
                       "conf": float(getattr(row, f"conf_{h}"))}
        test_items.append(item)

    report = {
        "source": "results/ and prepared/ from the training run on 2026-11-12 (scripts/train.py, evaluate.py)",
        "classes": {h: len(maps[h]) for h in HEADS},
        "data_steps": records(PREP / "table2_counts.csv"),
        "dedup": {"dropped": stats["dropped_duplicates"], "by_split": stats["dropped_by_split"],
                  "missing_images": stats["missing_images"], "max_hamming": stats["max_hamming"]},
        "final_counts": stats["final_counts"],
        "labels_table": records(PREP / "table1_labels.csv"),
        "training": {
            "epochs": int(len(history)),
            "best_val_score": float(history["val_score"].max()) if "val_score" in history else None,
            "seconds": float(history["seconds"].sum()) if "seconds" in history else None,
        },
        "test_metrics": records(RES / "test_metrics.csv"),
        "test_ci": records(RES / "test_ci.csv"),
        "top_confusions": records(RES / "top_confusions.csv")[:10],
        "audit": records(RES / "audit.csv"),
        "ablation": records(RES / "table4_ablation.csv"),
        "backbones": records(RES / "table5_backbones.csv"),
        "retrieval": records(RES / "table6_retrieval.csv"),
        "latency": records(RES / "latency.csv"),
        "test_sample": test_items,
    }
    out = SITE / "data" / "model_report.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"wrote {out}; {len(test_items)} test images in {img_test}")


if __name__ == "__main__":
    main()
