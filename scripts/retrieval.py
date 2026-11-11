"""Retrieval precision with the best.pt embeddings (handoff section 8, Table VI "before" row).

Queries: test images. Gallery: train images. Cosine similarity on the pooled features.
Precision@k = share of the top-k retrieved items with the same articleType, and with the same
articleType AND baseColour (queries/items with a masked colour count as no match for the
type+colour variant). Writes results/table6_retrieval.csv.

Run: python scripts/retrieval.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RESULTS, ROOT  # noqa: E402

KS = (1, 5, 10)


def main() -> None:
    emb = np.load(ROOT / "models" / "embeddings.npy")
    ids = pd.read_csv(ROOT / "models" / "embedding_ids.csv")
    split = pd.read_csv(ROOT / "prepared" / "split_final.csv").set_index("id").loc[ids["id"]]
    x = torch.nn.functional.normalize(torch.from_numpy(emb), dim=1)
    q = (split["split"] == "test").to_numpy()
    g = (split["split"] == "train").to_numpy()
    typ = split["y_articleType"].to_numpy()
    col = split["y_baseColour"].to_numpy()

    sims = x[q] @ x[g].T
    top = sims.topk(max(KS), dim=1).indices.numpy()
    gt, gc = typ[g][top], col[g][top]
    qt, qc = typ[q][:, None], col[q][:, None]
    same_t = gt == qt
    same_tc = same_t & (gc == qc) & (qc >= 0) & (gc >= 0)

    row = {"model": "EfficientNet-B0 best.pt (before triplet fine-tuning)",
           "queries": int(q.sum()), "gallery": int(g.sum())}
    for k in KS:
        row[f"p@{k}_type"] = float(same_t[:, :k].mean())
        row[f"p@{k}_type_colour"] = float(same_tc[:, :k].mean())
    pd.DataFrame([row]).to_csv(RESULTS / "table6_retrieval.csv", index=False)
    print(row)


if __name__ == "__main__":
    main()
