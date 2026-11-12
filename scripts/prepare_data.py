"""Clean the Fashion Product Images labels and build a fixed train/val/test split.

Reads:  data/styles.csv, data/images.csv
Writes: prepared/split.csv          one row per kept product, with labels and split
        prepared/label_maps.json    class name -> index for every head
        prepared/table1_labels.csv  paper Table I  (label columns and how they are used)
        prepared/table2_counts.csv  paper Table II (image counts at each cleaning step)
        prepared/class_counts.csv   per-class counts in train/val/test for every head
        prepared/fig1_article_types.png  paper Fig. 1 (class distribution)

Decisions:
  1. Keep masterCategory Apparel, Footwear, Accessories only.
  2. Keep articleType classes with >= 100 images (after step 1). Rarer rows are dropped.
  3. Colour head: colours with >= 300 images, "Multi" excluded. Other colours -> label masked.
  4. Usage head: Casual, Sports, Ethnic, Formal. Others or missing -> label masked.
  5. Season and year are not heads (not visible in an image).
  6. Gender head: all 5 values.
Masked labels are stored as -1 and skipped by that head's loss during training.

Split: 70/15/15, stratified on articleType, grouped by product name so the same product
listed twice can't land in both train and test. Fixed seed for reproducibility.
"""

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "prepared"
SEED = 42

KEEP_MASTER = ["Apparel", "Footwear", "Accessories"]
MIN_TYPE = 100
MIN_COLOUR = 300
EXCLUDE_COLOURS = {"Multi"}
KEEP_USAGE = ["Casual", "Sports", "Ethnic", "Formal"]
COLUMNS = ["id", "gender", "masterCategory", "subCategory", "articleType",
           "baseColour", "season", "year", "usage", "productDisplayName"]


def read_styles(path: Path) -> tuple[pd.DataFrame, int]:
    """Parse styles.csv, repairing rows whose product name contains extra commas."""
    rows, repaired = [], 0
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == COLUMNS, f"unexpected columns: {header}"
        for parts in reader:
            if not parts:
                continue
            if len(parts) > len(COLUMNS):
                parts = parts[:9] + [",".join(parts[9:])]
                repaired += 1
            elif len(parts) < len(COLUMNS):
                parts = parts + [""] * (len(COLUMNS) - len(parts))
            rows.append(parts)
    df = pd.DataFrame(rows, columns=COLUMNS).replace("", np.nan)
    df["id"] = df["id"].astype(int)
    return df, repaired


def main() -> None:
    OUT.mkdir(exist_ok=True)
    counts = []  # Table II rows: (step, images)

    styles, repaired = read_styles(DATA / "styles.csv")
    counts.append(("All records in styles.csv", len(styles)))

    images = pd.read_csv(DATA / "images.csv")
    image_ids = set(images["filename"].str.replace(".jpg", "", regex=False).astype(int))
    df = styles[styles["id"].isin(image_ids)].copy()
    counts.append(("With an image entry", len(df)))

    df = df.drop_duplicates(subset="id")
    counts.append(("Unique product ids", len(df)))

    df = df[df["masterCategory"].isin(KEEP_MASTER)].copy()
    counts.append(("Apparel, Footwear, Accessories only", len(df)))

    type_counts = df["articleType"].value_counts()
    kept_types = sorted(type_counts[type_counts >= MIN_TYPE].index)
    df = df[df["articleType"].isin(kept_types)].copy()
    counts.append((f"Article types with >= {MIN_TYPE} images", len(df)))

    colour_counts = df["baseColour"].value_counts()
    kept_colours = sorted(c for c in colour_counts[colour_counts >= MIN_COLOUR].index
                          if c not in EXCLUDE_COLOURS)
    kept_genders = sorted(df["gender"].dropna().unique())

    label_maps = {
        "articleType": {c: i for i, c in enumerate(kept_types)},
        "baseColour": {c: i for i, c in enumerate(kept_colours)},
        "gender": {c: i for i, c in enumerate(kept_genders)},
        "usage": {c: i for i, c in enumerate(KEEP_USAGE)},
    }
    for head, mapping in label_maps.items():
        df[f"y_{head}"] = df[head].map(mapping).fillna(-1).astype(int)

    # Grouped, stratified split: 20 folds -> 14 train, 3 val, 3 test (70/15/15).
    groups = df["productDisplayName"].fillna("id_" + df["id"].astype(str)).str.lower().str.strip()
    sgkf = StratifiedGroupKFold(n_splits=20, shuffle=True, random_state=SEED)
    fold = np.empty(len(df), dtype=int)
    for k, (_, idx) in enumerate(sgkf.split(df, df["articleType"], groups)):
        fold[idx] = k
    df["split"] = np.where(fold < 3, "test", np.where(fold < 6, "val", "train"))
    for name in ["train", "val", "test"]:
        counts.append((f"  {name}", int((df["split"] == name).sum())))

    leak = set(groups[df["split"] == "train"]) & set(groups[df["split"] == "test"])
    assert not leak, f"{len(leak)} product names appear in both train and test"

    keep_cols = ["id", "split", "masterCategory", "subCategory", "articleType", "baseColour",
                 "gender", "usage", "productDisplayName",
                 "y_articleType", "y_baseColour", "y_gender", "y_usage"]
    df[keep_cols].sort_values("id").to_csv(OUT / "split.csv", index=False)
    (OUT / "label_maps.json").write_text(json.dumps(label_maps, indent=2), encoding="utf-8")

    # Table I: how each label column is used.
    masked = {h: int((df[f"y_{h}"] == -1).sum()) for h in label_maps}
    table1 = pd.DataFrame([
        ("articleType", styles["articleType"].nunique(), "Head", f"{type_counts.size} types after category filter; {len(kept_types)} with >= {MIN_TYPE} images kept, rarer rows dropped"),
        ("baseColour", styles["baseColour"].nunique(), "Head", f"{len(kept_colours)} colours with >= {MIN_COLOUR} images, Multi excluded; {masked['baseColour']} labels masked"),
        ("gender", styles["gender"].nunique(), "Head", f"all {len(kept_genders)} values; {masked['gender']} labels masked"),
        ("usage", styles["usage"].nunique(), "Head", f"{', '.join(KEEP_USAGE)}; {masked['usage']} labels masked"),
        ("masterCategory", styles["masterCategory"].nunique(), "Filter", f"kept {', '.join(KEEP_MASTER)}"),
        ("subCategory", styles["subCategory"].nunique(), "Not used", "kept for analysis only"),
        ("season", styles["season"].nunique(), "Excluded", "not visible in an image"),
        ("year", styles["year"].nunique(), "Excluded", "not visible in an image"),
        ("productDisplayName", None, "Grouping only", "groups duplicate listings in the split; never a model input"),
    ], columns=["column", "distinct_values_raw", "role", "use_in_final_model"])
    table1.to_csv(OUT / "table1_labels.csv", index=False)
    pd.DataFrame(counts, columns=["step", "images"]).to_csv(OUT / "table2_counts.csv", index=False)

    # Per-class counts per split, every head.
    parts = []
    for head in label_maps:
        ct = pd.crosstab(df[head].where(df[f"y_{head}"] >= 0, "(masked)"), df["split"])
        ct = ct.reindex(columns=["train", "val", "test"], fill_value=0).reset_index()
        ct.columns = ["class", "train", "val", "test"]
        ct.insert(0, "head", head)
        parts.append(ct)
    pd.concat(parts).to_csv(OUT / "class_counts.csv", index=False)

    # Fig. 1: article type distribution (log scale shows the long tail).
    vc = df["articleType"].value_counts()
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.barh(vc.index[::-1], vc.values[::-1], color="#4a6fa5")
    ax.set_xscale("log")
    ax.set_xlabel("Images (log scale)")
    ax.set_title(f"Article types kept ({len(vc)} classes, {len(df):,} images)")
    fig.tight_layout()
    fig.savefig(OUT / "fig1_article_types.png", dpi=150)

    imbalance = vc.max() / vc.min()
    report = [
        "# Data preparation report",
        "",
        f"- Rows in styles.csv: {len(styles):,} ({repaired} rows with commas in the product name repaired, none dropped).",
        f"- Kept after cleaning: {len(df):,} images, {len(kept_types)} article types.",
        f"- Largest / smallest kept article type: {vc.index[0]} ({vc.iloc[0]:,}) / {vc.index[-1]} ({vc.iloc[-1]:,}), imbalance ratio {imbalance:.0f}:1.",
        f"- Colour head: {len(kept_colours)} classes; usage head: {len(KEEP_USAGE)}; gender head: {len(kept_genders)}.",
        f"- Masked labels: {masked}.",
        f"- Split (seed {SEED}, stratified by article type, grouped by product name): "
        + ", ".join(f"{n} {int((df['split'] == n).sum()):,}" for n in ["train", "val", "test"]) + ".",
        "- No product name appears in both train and test (checked).",
        "- Image-level near-duplicate check still to do in Colab (needs the images).",
    ]
    (OUT / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
