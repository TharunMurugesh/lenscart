"""Export the trained model and catalogue embeddings from runs/<name>/best.pt.

Writes to models/ (git-ignored except model_config.json):
  best.pt               CPU state_dict only (torch.save(model.cpu().state_dict()))
  model_config.json     backbone, head sizes, input size, mean/std, label_maps path
  embeddings.npy        float32 pooled features for every id in prepared/split_final.csv
  embedding_ids.csv     ids in the same order as embeddings.npy

The embeddings only use train/val/test images as inputs, never labels, so this is not a
test-set evaluation.

Run: python scripts/export.py --name m1
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (IMG_SIZE, LABEL_MAPS_JSON, MEAN, ROOT, RUNS, STD, LensNet, eval_transform,  # noqa: E402
                    head_sizes, load_split, make_loader, predict)

MODELS = ROOT / "models"


def check_layout(model, sd: dict, backbone: str, sizes: dict) -> dict:
    """Assert the model is exactly: timm backbone (num_classes=0, pooled output) -> Dropout ->
    one nn.Linear per head, and return the state_dict key layout for model_config.json."""
    import timm
    import torch.nn as nn

    # the only submodules are backbone, dropout and heads
    assert [n for n, _ in model.named_children()] == ["backbone", "dropout", "heads"], \
        list(model.named_children())
    assert isinstance(model.dropout, nn.Dropout)
    assert list(model.heads.keys()) == list(sizes), list(model.heads.keys())
    for h, n in sizes.items():
        lin = model.heads[h]
        assert type(lin) is nn.Linear, type(lin)
        assert (lin.in_features, lin.out_features) == (model.feat_dim, n)

    # every key is either backbone.* or a head's weight/bias
    head_keys = {h: {"weight": f"heads.{h}.weight", "bias": f"heads.{h}.bias"} for h in sizes}
    expected_head = {k for d in head_keys.values() for k in d.values()}
    other = [k for k in sd if not k.startswith("backbone.") and k not in expected_head]
    assert not other, f"unexpected state_dict keys: {other}"
    assert expected_head <= set(sd), expected_head - set(sd)

    # the backbone part loads strictly into a plain timm model with no classifier
    plain = timm.create_model(backbone, pretrained=False, num_classes=0)
    bb_sd = {k[len("backbone."):]: v for k, v in sd.items() if k.startswith("backbone.")}
    plain.load_state_dict(bb_sd, strict=True)
    assert plain.num_features == model.feat_dim
    with torch.no_grad():
        x = torch.randn(2, 3, IMG_SIZE, IMG_SIZE)
        assert plain.eval()(x).shape == (2, model.feat_dim)
        assert torch.allclose(plain(x), model.backbone(x))

    return {
        "architecture": f"timm.create_model('{backbone}', pretrained=False, num_classes=0) "
                        "-> Dropout(0.2) -> one nn.Linear(feature_dim, n_classes) per head",
        "backbone_prefix": "backbone.",
        "backbone_create": {"model_name": backbone, "num_classes": 0},
        "head_keys": head_keys,
        "head_shapes": {h: [n, model.feat_dim] for h, n in sizes.items()},
        "state_dict_keys": len(sd),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="m1")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    run = RUNS / args.name
    info = json.loads((run / "run.json").read_text(encoding="utf-8"))
    sizes = head_sizes()
    model = LensNet(info["backbone"], sizes, pretrained=False)
    ck = torch.load(run / "best.pt", map_location="cpu", weights_only=False)
    model.load_state_dict(ck["model"])
    MODELS.mkdir(exist_ok=True)

    model = model.cpu().eval()
    sd = model.state_dict()
    layout = check_layout(model, sd, info["backbone"], sizes)
    torch.save(sd, MODELS / "best.pt")
    config = {
        **layout,
        "backbone": info["backbone"], "head_sizes": sizes, "heads": list(sizes),
        "feature_dim": model.feat_dim, "dropout": 0.2,
        "input_size": IMG_SIZE, "resize_before": 256, "pad_colour": "white",
        "mean": list(MEAN), "std": list(STD), "label_maps": "label_maps.json",
        "best_epoch": int(ck["epoch"]), "val_score": float(ck["best_score"]),
        "load": "LensNet(backbone, head_sizes, pretrained=False).load_state_dict(torch.load('best.pt'))",
    }
    (MODELS / "model_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    shutil.copy(LABEL_MAPS_JSON, MODELS / "label_maps.json")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    split = load_split(final=True)
    loader = make_loader(split, eval_transform(), 128, workers=args.workers)
    emb = predict(model, loader, device, want_embeddings=True)["embeddings"]
    assert emb.shape == (len(split), model.feat_dim), emb.shape
    np.save(MODELS / "embeddings.npy", emb.astype(np.float32))
    split[["id", "split", "articleType"]].to_csv(MODELS / "embedding_ids.csv", index=False)
    print(f"exported state_dict, config, embeddings {emb.shape} to {MODELS}")


if __name__ == "__main__":
    main()
