"""FashionCLIP baselines on the VAL split (handoff section 8, Table V-c and V-d). Never test.

V-c  linear probe: frozen FashionCLIP image embeddings + one logistic regression per head,
     fit on train, scored on val.
V-d  zero-shot (M6): cosine similarity between image and text-prompt embeddings, no training.

Writes runs/clip/{v_c,v_d}.json and caches embeddings in runs/clip/emb_<split>.npy.

Run: python scripts/clip_baselines.py
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from sklearn.linear_model import LogisticRegression
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HEADS, RESIZED, RUNS, SEED, class_names, head_metrics, load_split  # noqa: E402

MODEL_ID = "patrickjohncyh/fashion-clip"
OUT = RUNS / "clip"
GENDER_WORD = {"Men": "men's", "Women": "women's", "Boys": "boys'", "Girls": "girls'",
               "Unisex": "unisex"}


def prompts(head: str) -> list:
    names = class_names(head)
    if head == "articleType":
        return [f"a photo of a {c}" for c in names]
    if head == "baseColour":
        return [f"a photo of a {c.lower()} clothing item" for c in names]
    if head == "gender":
        return [f"a photo of {GENDER_WORD[c]} clothing" for c in names]
    return [f"a photo of {c.lower()} wear" for c in names]


@torch.no_grad()
def embed_images(model, proc, ids, device, batch=128) -> np.ndarray:
    out = []
    for i in tqdm(range(0, len(ids), batch), desc="clip images"):
        imgs = []
        for j in ids[i:i + batch]:
            with Image.open(RESIZED / f"{j}.jpg") as im:
                imgs.append(im.convert("RGB"))
        x = proc(images=imgs, return_tensors="pt")["pixel_values"].to(device)
        with torch.autocast(device_type=device.type, dtype=torch.float16,
                            enabled=device.type == "cuda"):
            f = model.get_image_features(pixel_values=x)
        out.append(torch.nn.functional.normalize(f.float(), dim=-1).cpu())
    return torch.cat(out).numpy().astype(np.float32)


def score(Y, preds) -> dict:
    row, f1s = {}, []
    for j, h in enumerate(HEADS):
        acc, f1, n = head_metrics(Y[:, j], preds[h])
        row[f"val_acc_{h}"], row[f"val_f1_{h}"], row[f"n_{h}"] = acc, f1, n
        f1s.append(f1)
    row["val_score"] = float(np.mean(f1s))
    return row


def main() -> None:
    from transformers import CLIPModel, CLIPProcessor

    OUT.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = CLIPModel.from_pretrained(MODEL_ID).to(device).eval()
    proc = CLIPProcessor.from_pretrained(MODEL_ID)

    split = load_split(final=True)
    data = {}
    for s in ("train", "val"):
        df = split[split["split"] == s].reset_index(drop=True)
        cache = OUT / f"emb_{s}.npy"
        t0 = time.time()
        if cache.exists():
            emb = np.load(cache)
            assert len(emb) == len(df)
        else:
            emb = embed_images(model, proc, df["id"].tolist(), device)
            np.save(cache, emb)
        print(f"{s}: {emb.shape} ({time.time() - t0:.0f}s)")
        data[s] = (emb, df[[f"y_{h}" for h in HEADS]].to_numpy())

    Xtr, Ytr = data["train"]
    Xva, Yva = data["val"]

    # V-c linear probe
    t0 = time.time()
    preds = {}
    for j, h in enumerate(HEADS):
        m = Ytr[:, j] >= 0
        clf = LogisticRegression(max_iter=2000, C=1.0, random_state=SEED)
        clf.fit(Xtr[m], Ytr[m, j])
        preds[h] = clf.predict(Xva)
    vc = {"run": "V-c", "model": f"FashionCLIP linear probe ({MODEL_ID})",
          **score(Yva, preds), "train_seconds": round(time.time() - t0, 1),
          "classifier": "sklearn LogisticRegression(max_iter=2000, C=1.0), L2-normalised features"}
    (OUT / "v_c.json").write_text(json.dumps(vc, indent=2), encoding="utf-8")
    print("V-c", {k: round(v, 4) for k, v in vc.items() if k.startswith("val_f1") or k == "val_score"})

    # V-d zero-shot
    preds, used = {}, {}
    with torch.no_grad():
        for h in HEADS:
            p = prompts(h)
            used[h] = p
            t = proc(text=p, return_tensors="pt", padding=True).to(device)
            tf = torch.nn.functional.normalize(model.get_text_features(**t).float(), dim=-1)
            preds[h] = (torch.from_numpy(Xva).to(device) @ tf.T).argmax(1).cpu().numpy()
    vd = {"run": "V-d", "model": f"FashionCLIP zero-shot ({MODEL_ID})", **score(Yva, preds),
          "train_seconds": 0, "prompts": used}
    (OUT / "v_d.json").write_text(json.dumps(vd, indent=2), encoding="utf-8")
    print("V-d", {k: round(v, 4) for k, v in vd.items() if k.startswith("val_f1") or k == "val_score"})


if __name__ == "__main__":
    main()
