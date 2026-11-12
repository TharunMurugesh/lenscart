"""Visual fingerprints (embeddings) for every product in the shop, for "visually similar" search.

Runs the same ONNX model the browser uses on each product photo, with the same preprocessing
(white-padded square, resized to 224, ImageNet normalisation), and writes:
  site/ai/catalog_emb.bin     float16, N x 1280, L2-normalised (row order = catalog_ids.json)
  site/ai/catalog_ids.json    product ids in the same order
  site/data/similar.json      {product_id: [12 most similar product ids]}  for product pages
  site/ai/catalog_meta.json   {product_id: [articleType, masterCategory]}  so photo search can
                              group the similarity ranking by type without a server call

Products come from the local MySQL `lenscart` database (XAMPP, root, no password).
Run: python scripts/build_catalog_embeddings.py
"""

import json
import subprocess
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
MYSQL = Path("C:/xampp/mysql/bin/mysql.exe")
K = 12


def products() -> list:
    out = subprocess.run([str(MYSQL), "-u", "root", "-N", "-B", "lenscart", "-e",
                          "SELECT id, image FROM products ORDER BY id"],
                         capture_output=True, text=True, check=True).stdout
    return [(int(a), b) for a, b in (line.split("\t") for line in out.strip().splitlines())]


def product_meta() -> dict:
    out = subprocess.run([str(MYSQL), "-u", "root", "-N", "-B", "lenscart", "-e",
                          "SELECT id, articleType, masterCategory FROM products ORDER BY id"],
                         capture_output=True, text=True, check=True).stdout
    return {a: [b, c] for a, b, c in (line.split("	") for line in out.strip().splitlines())}


def preprocess(path: Path, meta: dict) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    side = max(im.size)
    sq = Image.new("RGB", (side, side), (255, 255, 255))
    sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    sq = sq.resize((meta["input_size"],) * 2, Image.BILINEAR)
    x = (np.asarray(sq, dtype=np.float32) / 255 - np.array(meta["mean"], np.float32)) / np.array(meta["std"], np.float32)
    return x.transpose(2, 0, 1)


def main() -> None:
    meta = json.loads((SITE / "ai" / "lensnet_meta.json").read_text(encoding="utf-8"))
    sess = ort.InferenceSession(str(SITE / "ai" / "lensnet.onnx"), providers=["CPUExecutionProvider"])
    out_idx = meta["outputs"].index("embedding")
    rows = products()
    ids, embs = [], []
    for pid, image in rows:
        x = preprocess(SITE / image, meta)[None]
        e = sess.run(None, {"image": x})[out_idx][0]
        embs.append(e / (np.linalg.norm(e) + 1e-12))
        ids.append(pid)
    E = np.stack(embs).astype(np.float32)

    (SITE / "ai" / "catalog_emb.bin").write_bytes(E.astype(np.float16).tobytes())
    (SITE / "ai" / "catalog_ids.json").write_text(json.dumps({"dim": E.shape[1], "ids": ids}), encoding="utf-8")

    (SITE / "ai" / "catalog_meta.json").write_text(json.dumps(product_meta()), encoding="utf-8")

    sims = E @ E.T
    np.fill_diagonal(sims, -1)
    top = np.argsort(-sims, axis=1)[:, :K]
    similar = {str(ids[i]): [ids[j] for j in top[i]] for i in range(len(ids))}
    (SITE / "data").mkdir(exist_ok=True)
    (SITE / "data" / "similar.json").write_text(json.dumps(similar), encoding="utf-8")
    print(f"{len(ids)} products, dim {E.shape[1]}, catalog_emb.bin "
          f"{(SITE / 'ai' / 'catalog_emb.bin').stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
