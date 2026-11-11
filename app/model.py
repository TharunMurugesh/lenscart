"""M1: the multi-task model, built exactly as in docs/handoff.md section 6.

efficientnet_b0 -> 1280-d pooled features -> Dropout(0.2) -> one Linear per head.
If models/best.pt + models/model_config.json exist they are loaded; otherwise the
backbone is ImageNet-pretrained and the heads are random (placeholder mode).
"""
import json
from pathlib import Path

import numpy as np
import timm
import torch
import torch.nn as nn
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
DEFAULT_LABEL_MAPS = ROOT / "prepared" / "label_maps.json"
HEADS = ["articleType", "baseColour", "gender", "usage"]

DEFAULT_CONFIG = {
    "backbone": "efficientnet_b0",
    "input_size": 224,
    "mean": [0.485, 0.456, 0.406],
    "std": [0.229, 0.224, 0.225],
    "dropout": 0.2,
}


class LensCartNet(nn.Module):
    def __init__(self, backbone: str, head_sizes: dict, dropout: float = 0.2, pretrained: bool = True):
        super().__init__()
        self.backbone = timm.create_model(backbone, pretrained=pretrained, num_classes=0)
        feat = self.backbone.num_features  # 1280 for efficientnet_b0
        self.dropout = nn.Dropout(dropout)
        self.heads = nn.ModuleDict({h: nn.Linear(feat, n) for h, n in head_sizes.items()})

    def embed(self, x):
        return self.backbone(x)

    def forward(self, x):
        f = self.dropout(self.embed(x))
        return {h: head(f) for h, head in self.heads.items()}


class HeadOutput(nn.Module):
    """Wraps the model so Grad-CAM sees one head's logits as a plain tensor."""

    def __init__(self, model: LensCartNet, head: str):
        super().__init__()
        self.model, self.head = model, head

    def forward(self, x):
        return self.model(x)[self.head]


def _remap_state_dict(sd: dict, model: LensCartNet) -> dict:
    """Map a best.pt state_dict onto our module names.

    Section 6 fixes the architecture but not the attribute names, so heads are
    matched by shape (sizes 49/18/5/4 are distinct) and the backbone by stripping
    whatever prefix the trainer used.
    """
    target = model.state_dict()
    if set(sd) == set(target):
        return sd
    out = {}
    bb_keys = {k[len("backbone."):] for k in target if k.startswith("backbone.")}
    sizes = {model.heads[h].out_features: h for h in model.heads}
    feat = model.backbone.num_features
    for k, v in sd.items():
        if k.endswith(("weight", "bias")) and v.dim() in (1, 2) and v.shape[0] in sizes \
                and (v.dim() == 1 or v.shape[1] == feat):
            out[f"heads.{sizes[v.shape[0]]}.{k.rsplit('.', 1)[1]}"] = v
            continue
        parts = k.split(".")
        for i in range(len(parts)):
            sub = ".".join(parts[i:])
            if sub in bb_keys:
                out["backbone." + sub] = v
                break
    missing = set(target) - set(out)
    if missing:
        raise RuntimeError(f"best.pt does not match the section 6 model; missing {sorted(missing)[:5]}")
    return out


class Model:
    def __init__(self):
        cfg_path = MODELS / "model_config.json"
        weights = MODELS / "best.pt"
        self.config = dict(DEFAULT_CONFIG)
        if cfg_path.exists():
            self.config.update(json.loads(cfg_path.read_text()))
        lm_path = Path(self.config.get("label_maps", DEFAULT_LABEL_MAPS))
        if not lm_path.is_absolute():
            lm_path = ROOT / lm_path
        if not lm_path.exists():
            lm_path = DEFAULT_LABEL_MAPS
        label_maps = json.loads(lm_path.read_text())
        self.classes = {h: [n for n, _ in sorted(label_maps[h].items(), key=lambda kv: kv[1])] for h in HEADS}
        head_sizes = {h: len(self.classes[h]) for h in HEADS}

        self.placeholder = not weights.exists()
        self.net = LensCartNet(self.config["backbone"], head_sizes, self.config["dropout"],
                               pretrained=self.placeholder)
        if not self.placeholder:
            sd = torch.load(weights, map_location="cpu", weights_only=True)
            if isinstance(sd, dict) and "model" in sd and isinstance(sd["model"], dict):
                sd = sd["model"]
            self.net.load_state_dict(_remap_state_dict(sd, self.net))
        else:
            torch.manual_seed(0)
        self.net.eval()
        self.size = int(self.config["input_size"])
        self.mean = np.array(self.config["mean"], dtype=np.float32)
        self.std = np.array(self.config["std"], dtype=np.float32)

    def to_square(self, img: Image.Image) -> Image.Image:
        """Same as handoff section 5: longest side fitted, centred on white square."""
        img = img.convert("RGB")
        s = max(img.size)
        canvas = Image.new("RGB", (s, s), (255, 255, 255))
        canvas.paste(img, ((s - img.width) // 2, (s - img.height) // 2))
        return canvas

    def tensor(self, square: Image.Image) -> torch.Tensor:
        arr = np.asarray(square.resize((self.size, self.size), Image.BILINEAR), dtype=np.float32) / 255.0
        arr = (arr - self.mean) / self.std
        return torch.from_numpy(arr.transpose(2, 0, 1)).unsqueeze(0)

    @torch.no_grad()
    def predict(self, x: torch.Tensor, top: int = 3) -> dict:
        logits = self.net(x)
        out = {}
        for h in HEADS:
            p = torch.softmax(logits[h][0], 0)
            v, i = p.topk(min(top, len(p)))
            out[h] = [{"label": self.classes[h][j], "index": int(j), "prob": float(pv)}
                      for pv, j in zip(v.tolist(), i.tolist())]
        return out
