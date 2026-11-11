"""Resize images once, remove near-duplicates from val/test, zip the resized set (section 5).

Reads:  prepared/split.csv, data/images_dir.txt (written by get_data.py)
Writes: data/resized/<id>.jpg              256x256, white padded, JPEG q90
        results/dropped_duplicates.csv     val/test ids within phash distance <= 4 of a train image
        results/preprocess_stats.json      counts for notes.md
        prepared/split_final.csv           split.csv minus missing images and dropped duplicates
        lenscart_resized_256.zip           data/resized/ for the demo catalogue

Run: python scripts/preprocess.py [--workers 8] [--skip-zip]
"""

import argparse
import json
import os
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, RESIZED, RESULTS, ROOT, SPLIT_CSV, SPLIT_FINAL_CSV  # noqa: E402

SIZE = 256
MAX_DIST = 4
ZIP_PATH = ROOT / "lenscart_resized_256.zip"


def resize_one(args):
    src, dst = args
    """Resize longer side to 256, centre on white 256x256, save; return 64-bit phash as int."""
    import imagehash

    if not Path(dst).exists():
        with Image.open(src) as im:
            im = im.convert("RGB")
            w, h = im.size
            s = SIZE / max(w, h)
            im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
            canvas = Image.new("RGB", (SIZE, SIZE), (255, 255, 255))
            canvas.paste(im, ((SIZE - im.width) // 2, (SIZE - im.height) // 2))
            canvas.save(dst, "JPEG", quality=90)
    with Image.open(dst) as im:
        return int(str(imagehash.phash(im)), 16)


def popcount64(x: np.ndarray) -> np.ndarray:
    if hasattr(np, "bitwise_count"):
        return np.bitwise_count(x)
    return np.unpackbits(x.view(np.uint8).reshape(-1, 8), axis=1).sum(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    ap.add_argument("--skip-zip", action="store_true")
    args = ap.parse_args()

    image_dir = Path((DATA / "images_dir.txt").read_text(encoding="utf-8").strip())
    split = pd.read_csv(SPLIT_CSV)
    n_start = len(split)

    # drop ids without an image (recorded by get_data.py)
    exists = split["id"].map(lambda i: (image_dir / f"{i}.jpg").exists())
    missing = split[~exists]
    split = split[exists].reset_index(drop=True)

    RESIZED.mkdir(parents=True, exist_ok=True)
    jobs = [(str(image_dir / f"{i}.jpg"), str(RESIZED / f"{i}.jpg")) for i in split["id"]]
    hashes, failed = [], []
    with ProcessPoolExecutor(args.workers) as ex:
        futures = ex.map(resize_one, jobs, chunksize=64)
        it = iter(futures)
        for i in tqdm(range(len(jobs)), desc="resize+phash"):
            try:
                hashes.append(next(it))
            except Exception as e:  # unreadable image
                print(f"failed {split['id'].iloc[i]}: {e}")
                hashes.append(None)
                failed.append(int(split["id"].iloc[i]))
    if failed:
        keep = [h is not None for h in hashes]
        split = split[keep].reset_index(drop=True)
        hashes = [h for h in hashes if h is not None]
    split["phash"] = np.array(hashes, dtype=np.uint64)

    # near-duplicates: a val/test image is dropped if a train image with the SAME articleType
    # and baseColour is within MAX_DIST. pHash alone (grayscale, 64-bit) matched different
    # products that share a silhouette on a white background (see results/notes.md).
    key = split["articleType"].astype(str) + "|" + split["baseColour"].fillna("").astype(str)
    split["key"] = key
    tr = split[split["split"] == "train"]
    by_key = {k: (g["phash"].to_numpy(dtype=np.uint64), g["id"].to_numpy())
              for k, g in tr.groupby("key")}
    evals = split[split["split"] != "train"]
    dropped = []
    for _, row in tqdm(evals.iterrows(), total=len(evals), desc="dedup"):
        if row["key"] not in by_key:
            continue
        train_h, train_ids = by_key[row["key"]]
        d = popcount64(np.bitwise_xor(train_h, np.uint64(row["phash"])))
        j = int(d.argmin())
        if d[j] <= MAX_DIST:
            dropped.append({"id": int(row["id"]), "split": row["split"],
                            "articleType": row["articleType"], "baseColour": row["baseColour"],
                            "nearest_train_id": int(train_ids[j]), "hamming": int(d[j])})
    split = split.drop(columns=["key"])
    dropped_df = pd.DataFrame(dropped, columns=["id", "split", "articleType", "baseColour",
                                                "nearest_train_id", "hamming"])
    RESULTS.mkdir(exist_ok=True)
    dropped_df.to_csv(RESULTS / "dropped_duplicates.csv", index=False)

    final = split[~split["id"].isin(dropped_df["id"])].drop(columns=["phash"])
    final.to_csv(SPLIT_FINAL_CSV, index=False)

    stats = {
        "split_rows": n_start,
        "missing_images": int(len(missing)),
        "unreadable_images": len(failed),
        "unreadable_ids": failed,
        "dropped_duplicates": int(len(dropped_df)),
        "dropped_by_split": dropped_df["split"].value_counts().to_dict(),
        "final_counts": final["split"].value_counts().to_dict(),
        "final_rows": int(len(final)),
        "max_hamming": MAX_DIST,
    }
    (RESULTS / "preprocess_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))

    if not args.skip_zip:
        print(f"zipping {RESIZED} -> {ZIP_PATH}")
        with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_STORED) as z:
            for i in tqdm(split["id"], desc="zip"):
                z.write(RESIZED / f"{i}.jpg", f"resized/{i}.jpg")


if __name__ == "__main__":
    main()
