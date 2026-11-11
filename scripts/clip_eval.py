"""FashionCLIP baselines for paper Table V (handoff section 8): validation set only.

V-c  linear probe: frozen FashionCLIP image embeddings + one logistic regression per head,
     fitted on train, scored on val.
V-d  zero-shot (M6): no training. Each class becomes a text prompt; the image is assigned
     to the prompt with the highest cosine similarity. Scored on val.

The test set is never touched here.

Reads:  prepared/split_final.csv, data/resized/<id>.jpg
Writes: results/table5_clip.csv     one row per method: val accuracy and macro F1 per head
        runs/clip/emb_<split>.npy  cached L2-normalised image embeddings (reused on rerun)

Run: python scripts/clip_eval.py [--batch 128] [--workers 4]
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from sklearn.linear_model import LogisticRegression
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HEADS, RESIZED, RESULTS, RUNS, class_names, head_metrics, load_split, seed_everything  # noqa: E402

MODEL_ID = "patrickjohncyh/fashion-clip"
GENDER_WORDS = {"Boys": "boys'", "Girls": "girls'", "Men": "men's", "Unisex": "unisex", "Women": "women's"}


def prompts(head: str) -> list:
    """Prompt per class, in label-index order (wording fixed by handoff section 8)."""
    names = class_names(head)
    if head == "articleType":
        return [f"a photo of a {c}" for c in names]
    if head == "baseColour":
        return [f"a photo of a {c.lower()} clothing item" for c in names]
    if head == "gender":
        return [f"a photo of {GENDER_WORDS[c]} clothing" for c in names]
    if head == "usage":
        return [f"a photo of {c.lower()} wear" for c in names]
    raise ValueError(head)


class Images(Dataset):
    def __init__(self, ids):
        self.ids = list(ids)

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, i):
        with Image.open(RESIZED / f"{self.ids[i]}.jpg") as im:
            return im.convert("RGB")


@torch.no_grad()
def image_embeddings(model, processor, ids, device, batch, workers) -> np.ndarray:
    loader = DataLoader(Images(ids), batch_size=batch, num_workers=workers,
                        collate_fn=lambda imgs: imgs)
    out = []
    for imgs in loader:
        px = processor(images=imgs, return_tensors="pt")["pixel_values"].to(device)
        with torch.autocast(device_type=device.type, dtype=torch.float16,
                            enabled=device.type == "cuda"):
            e = model.get_image_features(pixel_values=px)
        out.append(torch.nn.functional.normalize(e.float(), dim=-1).cpu())
    return torch.cat(out).numpy().astype(np.float32)


@torch.no_grad()
def text_embeddings(model, processor, texts, device) -> np.ndarray:
    tok = processor(text=texts, return_tensors="pt", padding=True).to(device)
    e = model.get_text_features(**tok)
    return torch.nn.functional.normalize(e.float(), dim=-1).cpu().numpy()


def cached(name: str, fn) -> np.ndarray:
    path = RUNS / "clip" / f"emb_{name}.npy"
    if path.exists():
        return np.load(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    arr = fn()
    np.save(path, arr)
    return arr


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    from transformers import CLIPModel, CLIPProcessor

    seed_everything()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    df = load_split(final=True)
    train, val = df[df["split"] == "train"], df[df["split"] == "val"]

    model = CLIPModel.from_pretrained(MODEL_ID).to(device).eval()
    processor = CLIPProcessor.from_pretrained(MODEL_ID)

    t0 = time.time()
    e_train = cached("train", lambda: image_embeddings(model, processor, train["id"], device, args.batch, args.workers))
    e_val = cached("val", lambda: image_embeddings(model, processor, val["id"], device, args.batch, args.workers))
    embed_s = time.time() - t0

    rows = []

    # V-c: linear probe
    t0 = time.time()
    row = {"run": "V-c", "method": "FashionCLIP linear probe"}
    f1s = []
    for h in HEADS:
        ytr, yva = train[f"y_{h}"].to_numpy(), val[f"y_{h}"].to_numpy()
        m = ytr >= 0
        clf = LogisticRegression(max_iter=2000, class_weight="balanced")
        clf.fit(e_train[m], ytr[m])
        acc, f1, n = head_metrics(yva, clf.predict(e_val))
        row[f"val_acc_{h}"], row[f"val_f1_{h}"] = acc, f1
        f1s.append(f1)
    row["val_mean_f1"] = float(np.mean(f1s))
    row["seconds"] = round(time.time() - t0 + embed_s, 1)
    rows.append(row)

    # V-d: zero-shot
    t0 = time.time()
    row = {"run": "V-d", "method": "FashionCLIP zero-shot"}
    f1s = []
    for h in HEADS:
        t = text_embeddings(model, processor, prompts(h), device)
        pred = (e_val @ t.T).argmax(1)
        acc, f1, n = head_metrics(val[f"y_{h}"].to_numpy(), pred)
        row[f"val_acc_{h}"], row[f"val_f1_{h}"] = acc, f1
        f1s.append(f1)
    row["val_mean_f1"] = float(np.mean(f1s))
    row["seconds"] = round(time.time() - t0, 1)
    rows.append(row)

    RESULTS.mkdir(exist_ok=True)
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "table5_clip.csv", index=False)
    print(out.to_string(index=False))
    print(f"image embedding time (train+val): {embed_s:.0f}s on {device}")


if __name__ == "__main__":
    main()
