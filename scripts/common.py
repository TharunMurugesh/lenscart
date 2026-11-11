"""Shared paths, data loading, model and metrics for training and evaluation.

Paths can be redirected with environment variables (useful on Colab, where outputs
should live on Google Drive):
  LENSCART_ROOT  repo root (default: parent of this folder)
  LENSCART_DATA  dataset folder (default: <root>/data)
  LENSCART_RUNS  checkpoints and per-run outputs (default: <root>/runs)
"""

import json
import os
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import accuracy_score, f1_score
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms as T

ROOT = Path(os.environ.get("LENSCART_ROOT", Path(__file__).resolve().parent.parent))
DATA = Path(os.environ.get("LENSCART_DATA", ROOT / "data"))
RUNS = Path(os.environ.get("LENSCART_RUNS", ROOT / "runs"))
PREPARED = ROOT / "prepared"
RESULTS = ROOT / "results"
RESIZED = DATA / "resized"

SPLIT_CSV = PREPARED / "split.csv"
SPLIT_FINAL_CSV = PREPARED / "split_final.csv"
LABEL_MAPS_JSON = PREPARED / "label_maps.json"

HEADS = ["articleType", "baseColour", "gender", "usage"]
SEED = 42
IMG_SIZE = 224
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


def load_label_maps() -> dict:
    with open(LABEL_MAPS_JSON, encoding="utf-8") as f:
        return json.load(f)


def head_sizes() -> dict:
    maps = load_label_maps()
    return {h: len(maps[h]) for h in HEADS}


def class_names(head: str) -> list:
    m = load_label_maps()[head]
    return [name for name, _ in sorted(m.items(), key=lambda kv: kv[1])]


def seed_everything(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def seed_worker(worker_id: int) -> None:
    s = torch.initial_seed() % 2**32
    np.random.seed(s)
    random.seed(s)


def load_split(final: bool = True) -> pd.DataFrame:
    path = SPLIT_FINAL_CSV if final else SPLIT_CSV
    if final and not path.exists():
        raise FileNotFoundError(f"{path} not found; run scripts/preprocess.py first")
    return pd.read_csv(path)


# ---------------------------------------------------------------- transforms

def train_transform(augment: bool = True) -> T.Compose:
    if not augment:
        return eval_transform()
    return T.Compose([
        T.RandomResizedCrop(IMG_SIZE, scale=(0.8, 1.0)),
        T.RandomHorizontalFlip(),
        T.RandomRotation(10, fill=(255, 255, 255)),
        # brightness/contrast only: hue or saturation jitter would break colour labels
        T.ColorJitter(brightness=0.1, contrast=0.1),
        T.ToTensor(),
        T.Normalize(MEAN, STD),
    ])


def eval_transform() -> T.Compose:
    return T.Compose([T.Resize(IMG_SIZE), T.ToTensor(), T.Normalize(MEAN, STD)])


# ---------------------------------------------------------------- data

class FashionDataset(Dataset):
    def __init__(self, df: pd.DataFrame, transform, image_dir: Path = RESIZED):
        self.ids = df["id"].to_numpy()
        self.labels = df[[f"y_{h}" for h in HEADS]].to_numpy(dtype=np.int64)
        self.transform = transform
        self.image_dir = Path(image_dir)

    def __len__(self) -> int:
        return len(self.ids)

    def __getitem__(self, i):
        with Image.open(self.image_dir / f"{self.ids[i]}.jpg") as im:
            img = im.convert("RGB")
        return self.transform(img), torch.from_numpy(self.labels[i])


def make_loader(df, transform, batch_size=64, shuffle=False, workers=None, seed=SEED):
    if workers is None:
        workers = min(8, os.cpu_count() or 1)
    g = torch.Generator()
    g.manual_seed(seed)
    return DataLoader(
        FashionDataset(df, transform),
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=workers,
        pin_memory=torch.cuda.is_available(),
        persistent_workers=workers > 0,
        worker_init_fn=seed_worker,
        generator=g,
        drop_last=False,
    )


def class_weights(train_df: pd.DataFrame, sizes: dict) -> dict:
    """w_c = 1/sqrt(count_c) from the train split, normalised to mean 1.

    Classes with no train examples get weight 0 before normalisation (none expected).
    """
    out = {}
    for h in HEADS:
        y = train_df[f"y_{h}"].to_numpy()
        counts = np.bincount(y[y >= 0], minlength=sizes[h]).astype(np.float64)
        w = np.where(counts > 0, 1.0 / np.sqrt(np.maximum(counts, 1)), 0.0)
        w = w / w[w > 0].mean()
        out[h] = torch.tensor(w, dtype=torch.float32)
    return out


# ---------------------------------------------------------------- model

class LensNet(nn.Module):
    """Pretrained backbone -> global pooled features -> dropout -> one linear head per task."""

    def __init__(self, backbone: str = "efficientnet_b0", sizes: dict | None = None,
                 pretrained: bool = True, dropout: float = 0.2):
        super().__init__()
        import timm

        sizes = sizes or head_sizes()
        self.backbone = timm.create_model(backbone, pretrained=pretrained, num_classes=0)
        self.feat_dim = self.backbone.num_features
        self.dropout = nn.Dropout(dropout)
        self.heads = nn.ModuleDict({h: nn.Linear(self.feat_dim, n) for h, n in sizes.items()})

    def embed(self, x):
        return self.backbone(x)

    def forward(self, x):
        f = self.dropout(self.backbone(x))
        return {h: head(f) for h, head in self.heads.items()}


class MultiHeadLoss(nn.Module):
    """Sum over heads of weighted cross-entropy; label -1 is skipped.

    A head whose labels are all masked in a batch contributes 0 (plain CE would give NaN).
    """

    def __init__(self, weights: dict | None):
        super().__init__()
        self.losses = nn.ModuleDict({
            h: nn.CrossEntropyLoss(weight=(weights[h] if weights else None), ignore_index=-1)
            for h in HEADS
        })

    def forward(self, logits: dict, y: torch.Tensor):
        total = 0.0
        for j, h in enumerate(HEADS):
            t = y[:, j]
            if (t >= 0).any():
                total = total + self.losses[h](logits[h].float(), t)
        return total


# ---------------------------------------------------------------- metrics

def head_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> tuple:
    """Accuracy and macro F1 over rows with a known label. Returns (acc, f1, n)."""
    m = y_true >= 0
    if m.sum() == 0:
        return float("nan"), float("nan"), 0
    yt, yp = y_true[m], y_pred[m]
    return (accuracy_score(yt, yp), f1_score(yt, yp, average="macro", zero_division=0),
            int(m.sum()))


@torch.no_grad()
def predict(model, loader, device, criterion=None, amp=True, want_embeddings=False):
    """Run the model over a loader. Returns dict with labels, logits per head, mean loss,
    and optionally pooled embeddings."""
    model.eval()
    labels, logits, embs = [], {h: [] for h in HEADS}, []
    loss_sum, n = 0.0, 0
    use_amp = amp and device.type == "cuda"
    for x, y in loader:
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
            f = model.embed(x)
            out = {h: head(model.dropout(f)) for h, head in model.heads.items()}
            if criterion is not None:
                loss_sum += float(criterion(out, y)) * x.size(0)
                n += x.size(0)
        labels.append(y.cpu())
        for h in HEADS:
            logits[h].append(out[h].float().cpu())
        if want_embeddings:
            embs.append(f.float().cpu())
    res = {
        "labels": torch.cat(labels).numpy(),
        "logits": {h: torch.cat(v).numpy() for h, v in logits.items()},
        "loss": loss_sum / n if n else float("nan"),
    }
    if want_embeddings:
        res["embeddings"] = torch.cat(embs).numpy().astype(np.float32)
    return res


def summarise(pred: dict) -> dict:
    """Per-head val accuracy / macro F1, plus the val score (mean macro F1 over heads)."""
    row = {}
    f1s = []
    for j, h in enumerate(HEADS):
        acc, f1, _ = head_metrics(pred["labels"][:, j], pred["logits"][h].argmax(1))
        row[f"val_acc_{h}"] = acc
        row[f"val_f1_{h}"] = f1
        f1s.append(f1)
    row["val_score"] = float(np.mean(f1s))
    return row
