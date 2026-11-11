"""Train the multi-head classifier (handoff section 6) and the short variant runs (section 8).

Every run writes to runs/<name>/:
  last.pt       model + optimiser + scheduler + epoch + history (resume point)
  best.pt       same format, best val score so far
  history.csv   one row per epoch
  run.json      settings, best epoch, best val metrics, total training seconds

Re-running the same command resumes from last.pt.

Main model (M1):     python scripts/train.py --name m1
Short schedule:      python scripts/train.py --name iv_b --stage-a 2 --stage-b 4
Frozen only (IV-a):  python scripts/train.py --name iv_a --stage-a 6 --stage-b 0
No class weights:    ... --no-weights        No augmentation: ... --no-aug
Other backbone:      ... --backbone resnet50
Background swap:     ... --bg-dir <folder of photos>   (robustness run IV-e)
"""

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (HEADS, RUNS, SEED, MultiHeadLoss, LensNet, class_weights,  # noqa: E402
                    eval_transform, head_sizes, load_split, make_loader, predict, seed_everything,
                    summarise, train_transform)


class BackgroundSwap:
    """With probability p, replace near-white background pixels (>240 in all channels)
    with a random real photo. Applied to the 256x256 PIL image before augmentation."""

    def __init__(self, bg_dir: Path, p: float = 0.5):
        self.files = sorted(f for f in Path(bg_dir).rglob("*")
                            if f.suffix.lower() in {".jpg", ".jpeg", ".png"})
        if not self.files:
            raise FileNotFoundError(f"no background photos in {bg_dir}")
        self.p = p

    def __call__(self, img: Image.Image) -> Image.Image:
        if random.random() >= self.p:
            return img
        with Image.open(random.choice(self.files)) as bg:
            bg = bg.convert("RGB").resize(img.size)
        a = np.asarray(img)
        mask = (a > 240).all(axis=2)
        out = np.where(mask[..., None], np.asarray(bg), a)
        return Image.fromarray(out.astype(np.uint8))


def build_optimizer(model, stage: str, n_epochs_b: int):
    if stage == "A":
        params = [{"params": model.heads.parameters(), "lr": 1e-3}]
        opt = torch.optim.AdamW(params, weight_decay=1e-4)
        sched = None
    else:
        params = [{"params": model.backbone.parameters(), "lr": 1e-4},
                  {"params": model.heads.parameters(), "lr": 1e-3}]
        opt = torch.optim.AdamW(params, weight_decay=1e-4)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, n_epochs_b))
    return opt, sched


def set_backbone_trainable(model, trainable: bool) -> None:
    for p in model.backbone.parameters():
        p.requires_grad = trainable


def save_ckpt(path: Path, model, opt, sched, scaler, epoch, stage, history, best_score, bad):
    tmp = path.with_suffix(".tmp")
    torch.save({
        "model": model.state_dict(),
        "optimizer": opt.state_dict(),
        "scheduler": sched.state_dict() if sched else None,
        "scaler": scaler.state_dict(),
        "epoch": epoch, "stage": stage, "history": history,
        "best_score": best_score, "bad_epochs": bad,
    }, tmp)
    tmp.replace(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--backbone", default="efficientnet_b0")
    ap.add_argument("--stage-a", type=int, default=3, help="epochs with frozen backbone")
    ap.add_argument("--stage-b", type=int, default=15, help="max epochs with full fine-tuning")
    ap.add_argument("--patience", type=int, default=3)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--no-weights", action="store_true")
    ap.add_argument("--no-aug", action="store_true")
    ap.add_argument("--bg-dir", type=Path, default=None)
    args = ap.parse_args()

    seed_everything(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out = RUNS / args.name
    out.mkdir(parents=True, exist_ok=True)

    split = load_split(final=True)
    train_df = split[split["split"] == "train"].reset_index(drop=True)
    val_df = split[split["split"] == "val"].reset_index(drop=True)
    sizes = head_sizes()

    tf = train_transform(augment=not args.no_aug)
    if args.bg_dir:
        import torchvision.transforms as T
        tf = T.Compose([BackgroundSwap(args.bg_dir), tf])
    train_loader = make_loader(train_df, tf, args.batch, shuffle=True, workers=args.workers)
    val_loader = make_loader(val_df, eval_transform(), args.batch * 2, workers=args.workers)

    model = LensNet(args.backbone, sizes).to(device)
    weights = None if args.no_weights else class_weights(train_df, sizes)
    if weights:
        weights = {h: w.to(device) for h, w in weights.items()}
    criterion = MultiHeadLoss(weights).to(device)
    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    total_epochs = args.stage_a + args.stage_b
    start_epoch, history, best_score, bad = 1, [], -math.inf, 0
    stage = "A" if args.stage_a > 0 else "B"
    set_backbone_trainable(model, stage == "B")
    opt, sched = build_optimizer(model, stage, args.stage_b)

    last = out / "last.pt"
    if last.exists():
        ck = torch.load(last, map_location=device, weights_only=False)
        model.load_state_dict(ck["model"])
        stage = ck["stage"]
        set_backbone_trainable(model, stage == "B")
        opt, sched = build_optimizer(model, stage, args.stage_b)
        opt.load_state_dict(ck["optimizer"])
        if sched and ck["scheduler"]:
            sched.load_state_dict(ck["scheduler"])
        scaler.load_state_dict(ck["scaler"])
        start_epoch = ck["epoch"] + 1
        history, best_score, bad = ck["history"], ck["best_score"], ck["bad_epochs"]
        print(f"resumed {args.name} from epoch {ck['epoch']} (stage {stage})")

    stopped_early = False
    for epoch in range(start_epoch, total_epochs + 1):
        if stage == "B" and bad >= args.patience:
            stopped_early = True
            break
        if epoch == args.stage_a + 1 and stage == "A":
            stage = "B"
            set_backbone_trainable(model, True)
            opt, sched = build_optimizer(model, stage, args.stage_b)
            bad = 0

        t0 = time.time()
        model.train()
        if stage == "A":
            model.backbone.eval()  # frozen backbone: keep BatchNorm statistics fixed too
        train_loader.generator.manual_seed(SEED + epoch)
        random.seed(SEED + epoch)
        loss_sum, n = 0.0, 0
        for x, y in tqdm(train_loader, desc=f"{args.name} ep{epoch} {stage}", leave=False):
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                loss = criterion(model(x), y)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            loss_sum += float(loss) * x.size(0)
            n += x.size(0)
        if sched:
            sched.step()

        val = predict(model, val_loader, device, criterion, amp=use_amp)
        row = {"epoch": epoch, "stage": stage, "train_loss": loss_sum / n,
               "val_loss": val["loss"], **summarise(val), "seconds": round(time.time() - t0, 1)}
        history.append(row)
        pd.DataFrame(history).to_csv(out / "history.csv", index=False)
        print(f"ep{epoch} {stage} train {row['train_loss']:.4f} val {row['val_loss']:.4f} "
              + " ".join(f"{h} {row[f'val_f1_{h}']:.3f}" for h in HEADS)
              + f" score {row['val_score']:.4f} ({row['seconds']}s)")

        if row["val_score"] > best_score:
            best_score, bad = row["val_score"], 0
            save_ckpt(out / "best.pt", model, opt, sched, scaler, epoch, stage, history,
                      best_score, bad)
        elif stage == "B":
            bad += 1
        save_ckpt(last, model, opt, sched, scaler, epoch, stage, history, best_score, bad)

    best_row = max(history, key=lambda r: r["val_score"])
    info = {
        "name": args.name, "backbone": args.backbone, "stage_a": args.stage_a,
        "stage_b": args.stage_b, "patience": args.patience, "batch": args.batch,
        "class_weights": not args.no_weights, "augmentation": not args.no_aug,
        "bg_swap": str(args.bg_dir) if args.bg_dir else None,
        "epochs_run": len(history), "stopped_early": stopped_early,
        "best_epoch": best_row["epoch"], "best": best_row,
        "train_seconds": round(sum(r["seconds"] for r in history), 1),
        "device": torch.cuda.get_device_name(0) if use_amp else "cpu",
    }
    (out / "run.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"done: best epoch {best_row['epoch']} val score {best_row['val_score']:.4f}")


if __name__ == "__main__":
    main()
