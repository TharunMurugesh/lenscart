"""Upload -> M2 background removal -> M1 predictions -> M3 Grad-CAM + focus -> M7 palette.

Everything stays in memory; nothing is written to disk.
"""
import base64
import io
import os
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from sklearn.cluster import KMeans

from .model import HEADS, HeadOutput, Model

WORK_MAX = 1024  # mask, heat maps and focus score are computed at this square size (or less)
SHOW_MAX = 512   # images sent to the browser

_model = None
_rembg = None
_cams = {}


def model() -> Model:
    global _model
    if _model is None:
        _model = Model()
    return _model


def _rembg_session():
    global _rembg
    if _rembg is None:
        from rembg import new_session
        _rembg = new_session("u2net")
    return _rembg


def _cam(head: str):
    if head not in _cams:
        m = model()
        _cams[head] = GradCAM(model=HeadOutput(m.net, head), target_layers=[m.net.backbone.conv_head])
    return _cams[head]


def _b64(img: Image.Image, fmt="JPEG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=88) if fmt == "JPEG" else img.save(buf, format=fmt)
    return f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode()


def _fit(img: Image.Image, n: int) -> Image.Image:
    return img if img.width <= n else img.resize((n, n), Image.BILINEAR)


def u2net_available() -> bool:
    """True only if the u2net weights are already on disk, so rembg never auto-downloads."""
    home = Path(os.environ.get("U2NET_HOME", Path.home() / ".u2net"))
    return (home / "u2net.onnx").exists()


def threshold_mask(rgb: np.ndarray) -> np.ndarray:
    """Fallback for white catalogue backgrounds: >240 in all channels = background,
    then morphological close, keep the largest component, fill holes."""
    fg = np.uint8(~(rgb > 240).all(axis=2)) * 255
    k = max(3, rgb.shape[0] // 100) | 1
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    if n <= 1:
        return np.zeros(rgb.shape[:2], np.float32)
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    fg = np.uint8(labels == biggest) * 255
    contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(fg)
    cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)
    return filled.astype(np.float32) / 255.0


def garment_mask(square: Image.Image, rgb: np.ndarray):
    """M2: mask in [0, 1] at the square's size, plus the method used."""
    if u2net_available():
        from rembg import remove
        m = remove(square, session=_rembg_session(), only_mask=True)
        return np.asarray(m.convert("L"), dtype=np.float32) / 255.0, "u2net"
    return threshold_mask(rgb), "threshold"


def heat_maps(x, preds, size: int) -> dict:
    """M3: Grad-CAM for each head's top answer, upsampled to size x size."""
    out = {}
    for h in HEADS:
        cam = _cam(h)(input_tensor=x, targets=[ClassifierOutputTarget(preds[h][0]["index"])])[0]
        out[h] = cv2.resize(cam, (size, size), interpolation=cv2.INTER_LINEAR)
    return out


def focus_score(cam: np.ndarray, mask: np.ndarray):
    total = float(cam.sum())
    return None if total <= 0 else float((cam * mask).sum() / total)


def overlay(square_rgb: np.ndarray, cam: np.ndarray) -> Image.Image:
    heat = cv2.applyColorMap(np.uint8(255 * np.clip(cam, 0, 1)), cv2.COLORMAP_JET)
    heat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)
    return Image.fromarray(np.uint8(0.55 * square_rgb + 0.45 * heat))


def palette(square_rgb: np.ndarray, mask: np.ndarray, k: int = 5) -> list:
    """M7: k-means on garment pixels only (mask > 0.5)."""
    px = square_rgb[mask > 0.5].reshape(-1, 3).astype(np.float32)
    if len(px) < k:
        return []
    rng = np.random.default_rng(0)
    if len(px) > 20000:
        px = px[rng.choice(len(px), 20000, replace=False)]
    km = KMeans(n_clusters=k, n_init=4, random_state=0).fit(px)
    counts = np.bincount(km.labels_, minlength=k)
    order = np.argsort(-counts)
    return [{"hex": "#%02x%02x%02x" % tuple(int(round(c)) for c in km.cluster_centers_[i]),
             "share": float(counts[i] / counts.sum())} for i in order]


_lock = threading.Lock()  # Grad-CAM hooks are shared state: one analysis at a time


def analyze(raw: bytes) -> dict:
    with _lock:
        return _analyze(raw)


def _analyze(raw: bytes) -> dict:
    t = {}
    t0 = time.perf_counter()
    m = model()
    img = Image.open(io.BytesIO(raw))
    img.load()
    square = m.to_square(img)
    work = _fit(square, WORK_MAX)
    size = work.width
    rgb = np.asarray(work, dtype=np.float32)
    t["load"] = time.perf_counter() - t0

    s = time.perf_counter()
    mask, mask_method = garment_mask(work, rgb)
    t["m2_background"] = time.perf_counter() - s

    s = time.perf_counter()
    x = m.tensor(square)
    preds = m.predict(x)
    t["m1_predict"] = time.perf_counter() - s

    s = time.perf_counter()
    cams = heat_maps(x, preds, size)
    t["m3_gradcam"] = time.perf_counter() - s

    s = time.perf_counter()
    pal = palette(rgb, mask)
    t["m7_palette"] = time.perf_counter() - s

    s = time.perf_counter()
    cutout = Image.fromarray(np.dstack([np.uint8(rgb), np.uint8(255 * mask)]), "RGBA")
    show = lambda im: _b64(_fit(im, SHOW_MAX))
    heads = {}
    for h in HEADS:
        heads[h] = {"top": preds[h], "focus": focus_score(cams[h], mask),
                    "heatmap": show(overlay(rgb, cams[h]))}
    t["encode"] = time.perf_counter() - s
    t["total"] = time.perf_counter() - t0

    return {
        "placeholder": m.placeholder,
        "original": show(work),
        "cleaned": _b64(_fit(cutout, SHOW_MAX), "PNG"),
        "mask_method": mask_method,
        "mask_share": float((mask > 0.5).mean()),
        "heads": heads,
        "palette": pal,
        "timings": {k: round(v, 3) for k, v in t.items()},
        "work_size": size,
    }
