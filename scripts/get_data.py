"""Download and unpack the full Fashion Product Images dataset (section 4 of the handoff).

Needs KAGGLE_API_TOKEN set in the shell (never in a file). Steps:
  1. kaggle datasets download paramaggarwal/fashion-product-images-dataset -p data
  2. unzip into data/ and delete the zip
  3. find the folder holding <id>.jpg files; if a nested duplicate copy exists, delete it
  4. check every id in prepared/split.csv has an image; write the folder path to
     data/images_dir.txt and missing ids to results/missing_images.csv

Run: python scripts/get_data.py            (download + unzip + check)
     python scripts/get_data.py --check    (only steps 3-4, data already unpacked)
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, RESULTS, SPLIT_CSV  # noqa: E402

DATASET = "paramaggarwal/fashion-product-images-dataset"
ZIP_NAME = "fashion-product-images-dataset.zip"


def download() -> Path:
    if not os.environ.get("KAGGLE_API_TOKEN"):
        sys.exit("KAGGLE_API_TOKEN is not set in this shell. Get it from Vinay privately.")
    DATA.mkdir(parents=True, exist_ok=True)
    zip_path = DATA / ZIP_NAME
    if zip_path.exists():
        print(f"zip already present: {zip_path}")
        return zip_path
    cmd = ["kaggle", "datasets", "download", DATASET, "-p", str(DATA)]
    print("running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    if not zip_path.exists():
        zips = list(DATA.glob("*.zip"))
        if len(zips) != 1:
            sys.exit(f"expected one zip in {DATA}, found {zips}")
        zip_path = zips[0]
    return zip_path


def unzip(zip_path: Path) -> None:
    print(f"extracting {zip_path} ...")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(DATA)
    zip_path.unlink()
    print("extracted, zip deleted")


def image_dirs() -> list:
    """Every folder under data/ (excluding data/resized) that holds .jpg files, by count."""
    found = []
    for d in DATA.rglob("*"):
        if not d.is_dir() or d.name == "resized" or "resized" in d.parts:
            continue
        n = sum(1 for _ in d.glob("*.jpg"))
        if n > 1000:
            found.append((n, d))
    return sorted(found, key=lambda t: (-t[0], len(str(t[1]))))


def pick_image_dir() -> Path:
    dirs = image_dirs()
    if not dirs:
        sys.exit(f"no folder with .jpg images found under {DATA}")
    for n, d in dirs:
        print(f"  {n:6d} jpg  {d}")
    keep = dirs[0][1]
    # The archive can contain a nested duplicate (fashion-dataset/fashion-dataset/...).
    # Delete only folders that look like a full second copy of the kept one.
    for n, d in dirs[1:]:
        if n >= 0.9 * dirs[0][0]:
            dup_root = d.parent if d.name == "images" else d
            if keep.is_relative_to(dup_root):
                dup_root = d
            print(f"deleting duplicate image folder {dup_root}")
            shutil.rmtree(dup_root)
    return keep


def check(image_dir: Path) -> None:
    split = pd.read_csv(SPLIT_CSV)
    have = {p.stem for p in image_dir.glob("*.jpg")}
    missing = split[~split["id"].astype(str).isin(have)]
    RESULTS.mkdir(exist_ok=True)
    missing[["id", "split", "articleType"]].to_csv(RESULTS / "missing_images.csv", index=False)
    (DATA / "images_dir.txt").write_text(str(image_dir), encoding="utf-8")
    print(f"images folder: {image_dir}")
    print(f"split ids: {len(split)}, with image: {len(split) - len(missing)}, "
          f"missing: {len(missing)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="skip download/unzip")
    args = ap.parse_args()
    if not args.check:
        unzip(download())
    check(pick_image_dir())


if __name__ == "__main__":
    main()
