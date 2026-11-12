"""Convert the trained model (models/best.pt) to ONNX so it runs in the browser.

The exported graph takes one 224x224 image and returns, for every head:
  logits_<head>   (1, C)        class scores
  cam_<head>      (1, C, 7, 7)  class activation maps (CAM)
plus
  embedding       (1, 1280)     pooled features (for "similar items")

Why CAM is exact here: the model is backbone -> global average pool -> one linear layer per head.
For that design the class score is the average over the 7x7 grid of (W_c . F[:, i, j]) + b_c,
so W_c . F[:, i, j] is exactly how much each grid cell contributes to class c (Zhou et al., 2016).
For this architecture Grad-CAM reduces to the same map up to a constant factor.

Run:  python scripts/export_onnx.py             (writes site/ai/lensnet.onnx, checks it)
"""

import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import HEADS, LensNet, ROOT  # noqa: E402

MODELS = ROOT / "models"
OUT_DIR = ROOT / "site" / "ai"


class Exportable(nn.Module):
    def __init__(self, net: LensNet):
        super().__init__()
        self.net = net

    def forward(self, x):
        fmap = self.net.backbone.forward_features(x)          # (1, 1280, 7, 7)
        pooled = fmap.mean(dim=(2, 3))                          # same as timm's avg pool
        outs = []
        for h in HEADS:
            head = self.net.heads[h]
            outs.append(head(pooled))                           # logits
            outs.append(torch.einsum("ck,bkhw->bchw", head.weight, fmap))  # CAM
        outs.append(pooled)
        return tuple(outs)


def main() -> None:
    cfg = json.loads((MODELS / "model_config.json").read_text(encoding="utf-8"))
    net = LensNet(cfg["backbone"], cfg["head_sizes"], pretrained=False)
    net.load_state_dict(torch.load(MODELS / "best.pt", map_location="cpu"))
    net.eval()
    model = Exportable(net).eval()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "lensnet.onnx"
    names = [n for h in HEADS for n in (f"logits_{h}", f"cam_{h}")] + ["embedding"]
    x = torch.randn(1, 3, cfg["input_size"], cfg["input_size"])
    torch.onnx.export(model, (x,), str(path), input_names=["image"], output_names=names,
                      opset_version=17, dynamo=False)

    # parity check: ONNX vs PyTorch on random inputs, and pooled path vs the original forward
    import onnxruntime as ort
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    worst = 0.0
    for seed in range(3):
        torch.manual_seed(seed)
        x = torch.randn(1, 3, cfg["input_size"], cfg["input_size"])
        with torch.no_grad():
            ref = model(x)
            direct = net(x)
        got = sess.run(None, {"image": x.numpy()})
        for r, g in zip(ref, got):
            worst = max(worst, float(np.abs(r.numpy() - g).max()))
        for j, h in enumerate(HEADS):
            assert torch.allclose(ref[2 * j], direct[h], atol=1e-4), f"pooled path differs for {h}"
    size_mb = path.stat().st_size / 1e6
    print(f"wrote {path} ({size_mb:.1f} MB); max abs diff onnx vs torch: {worst:.2e}")
    assert worst < 1e-3, "ONNX output differs from PyTorch"

    # labels for the browser, in index order
    maps = json.loads((ROOT / "prepared" / "label_maps.json").read_text(encoding="utf-8"))
    labels = {h: [n for n, _ in sorted(maps[h].items(), key=lambda kv: kv[1])] for h in HEADS}
    meta = {"heads": HEADS, "labels": labels, "input_size": cfg["input_size"],
            "mean": cfg["mean"], "std": cfg["std"], "outputs": names}
    (OUT_DIR / "lensnet_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("wrote", OUT_DIR / "lensnet_meta.json")


if __name__ == "__main__":
    main()
