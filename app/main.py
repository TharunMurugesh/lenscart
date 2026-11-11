"""LensCart demo server.  Run:  .venv\\Scripts\\python -m uvicorn app.main:app --port 8000"""
import base64
import random
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from . import pipeline
from .model import HEADS, MODELS, ROOT

STATIC = Path(__file__).parent / "static"
RESULTS = ROOT / "results"
TEST_CSV = RESULTS / "test_predictions.csv"
RESIZED = ROOT / "data" / "resized"
MAX_UPLOAD = 15 * 1024 * 1024

app = FastAPI(title="LensCart")


@app.get("/api/status")
def status():
    m = pipeline.model()
    return {
        "placeholder": m.placeholder,
        "backbone": m.config["backbone"],
        "heads": {h: len(m.classes[h]) for h in HEADS},
        "has_weights": (MODELS / "best.pt").exists(),
        "has_test_predictions": TEST_CSV.exists(),
        "has_test_images": RESIZED.exists(),
    }


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    raw = await file.read()  # kept in memory only, never written to disk
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "Image is larger than 15 MB.")
    try:
        return await run_in_threadpool(pipeline.analyze, raw)
    except UnidentifiedImageError:
        raise HTTPException(400, "That file is not an image. Please upload a JPG or PNG photo.")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Could not analyse this image: {e}")


# ---------- Test mode ----------
_test = None


def _find(cols, head, *words):
    h = head.lower()
    for c in cols:
        cl = c.lower()
        if h in cl and any(w in cl for w in words):
            return c
    return None


def _load_test():
    """Reads results/test_predictions.csv. Column names are matched loosely
    (e.g. true_articleType / articleType_true / pred_articleType / conf_...)."""
    global _test
    if _test is None:
        df = pd.read_csv(TEST_CSV)
        cols = list(df.columns)
        idc = next((c for c in cols if c.lower() == "id"), cols[0])
        spec = {}
        for h in HEADS:
            tc = _find(cols, h, "true", "label", "gt")
            pc = _find([c for c in cols if c != tc], h, "pred")
            cc = _find(cols, h, "conf", "prob", "score")
            if tc and pc:
                spec[h] = (tc, pc, cc)
        _test = (df, idc, spec)
    return _test


@app.get("/api/test/next")
def test_next():
    if not TEST_CSV.exists():
        raise HTTPException(404, "results/test_predictions.csv is not here yet. It arrives with best.pt.")
    df, idc, spec = _load_test()
    if not spec:
        raise HTTPException(500, "test_predictions.csv has no recognisable true/pred columns.")
    row = df.iloc[random.randrange(len(df))]
    pid = str(row[idc])
    img = RESIZED / f"{pid}.jpg"
    image = ("data:image/jpeg;base64," + base64.b64encode(img.read_bytes()).decode()) if img.exists() else None
    heads = {}
    for h, (tc, pc, cc) in spec.items():
        true, pred = row[tc], row[pc]
        if pd.isna(true) or str(true) in ("", "-1"):
            continue  # masked label: not scored, same as the metrics
        heads[h] = {"true": str(true), "pred": str(pred),
                    "conf": None if cc is None or pd.isna(row[cc]) else float(row[cc]),
                    "correct": str(true) == str(pred)}
    return {"id": pid, "image": image, "heads": heads, "total": len(df)}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
