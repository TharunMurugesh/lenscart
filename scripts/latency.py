"""CPU inference time per image, batch 1, average over 50 val images (handoff section 8).

Times the model forward pass only (image already loaded and transformed), after 5 warm-up
images. Appends one row per run to results/latency.csv.

Run: python scripts/latency.py --runs iv_b v_b
"""

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import pandas as pd
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RESIZED, RESULTS, RUNS, LensNet, eval_transform, head_sizes, load_split  # noqa: E402

N, WARMUP = 50, 5


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    args = ap.parse_args()

    split = load_split(final=True)
    ids = split.loc[split["split"] == "val", "id"].head(N + WARMUP).tolist()
    tf = eval_transform()
    xs = []
    for i in ids:
        with Image.open(RESIZED / f"{i}.jpg") as im:
            xs.append(tf(im.convert("RGB")).unsqueeze(0))

    rows = []
    for name in args.runs:
        info = json.loads((RUNS / name / "run.json").read_text(encoding="utf-8"))
        model = LensNet(info["backbone"], head_sizes(), pretrained=False)
        ck = torch.load(RUNS / name / "best.pt", map_location="cpu", weights_only=False)
        model.load_state_dict(ck["model"])
        model.eval()
        times = []
        with torch.inference_mode():
            for k, x in enumerate(xs):
                t0 = time.perf_counter()
                model(x)
                if k >= WARMUP:
                    times.append(time.perf_counter() - t0)
        ms = 1000 * sum(times) / len(times)
        params = sum(p.numel() for p in model.parameters())
        rows.append({"run": name, "backbone": info["backbone"], "ms_per_image": round(ms, 2),
                     "images": len(times), "batch": 1, "params_millions": round(params / 1e6, 2),
                     "cpu": platform.processor(), "torch_threads": torch.get_num_threads()})
        print(rows[-1])

    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / "latency.csv"
    old = pd.read_csv(path) if path.exists() else pd.DataFrame()
    if len(old):
        old = old[~old["run"].isin(args.runs)]
    pd.concat([old, pd.DataFrame(rows)]).to_csv(path, index=False)


if __name__ == "__main__":
    main()
