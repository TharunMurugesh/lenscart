# Training on a Kaggle Notebook (no dataset download)

Why: the dataset is 23 GB. On Kaggle it is already on Kaggle's servers and can be attached to a
notebook, so nobody downloads it. The training scripts in `scripts/` run unchanged; only the
folders are redirected with environment variables.

## Before you start (once)
1. Log in to kaggle.com with the account that will run it.
2. **Phone-verify the account:** Settings → Phone verification. Without it, notebooks get no GPU
   and no internet.

## Create the notebook
1. kaggle.com → **Create → New Notebook**.
2. Right panel → **Session options**:
   - **Accelerator:** GPU P100 (or GPU T4 x2 if P100 isn't offered).
   - **Internet:** On.
3. Right panel → **Add Input** → search `paramaggarwal/fashion-product-images-dataset` → **Add**.
   It appears under `/kaggle/input/`. Read-only, no download.
4. Paste the cells below, one cell each.

### Cell 1: get the code
```python
!git clone -q https://github.com/VinayG759/LensCart.git /kaggle/working/LensCart
%cd /kaggle/working/LensCart
!git log --oneline -1
!pip install -q timm imagehash
```

### Cell 2: point the scripts at Kaggle's folders
```python
import os, glob
os.environ["LENSCART_DATA"] = "/kaggle/working/data"
os.environ["LENSCART_RUNS"] = "/kaggle/working/runs"
os.makedirs("/kaggle/working/data", exist_ok=True)

# find the folder that holds the <id>.jpg images (the dataset may contain a nested duplicate)
hits = glob.glob("/kaggle/input/**/images/15970.jpg", recursive=True)
print(hits)
image_dir = os.path.dirname(hits[0])
open("/kaggle/working/data/images_dir.txt", "w").write(image_dir)
print("using", image_dir, "-", len(os.listdir(image_dir)), "files")
!nvidia-smi --query-gpu=name,memory.total --format=csv
```

### Cell 3: resize once + near-duplicate removal (about 20–40 min, CPU)
```python
!python scripts/preprocess.py --workers 4
!cat results/preprocess_stats.json
```

### Cell 4: main model M1 (the important one)
```python
!python scripts/train.py --name m1 --workers 4
```

### Cell 5: final test evaluation (ONCE) + export
```python
!python scripts/evaluate.py --name m1 --workers 4
!python scripts/export.py --name m1 --workers 4
!cat results/test_metrics.csv
```

### Cell 6: comparison runs for paper Tables IV–V (val only, short schedule)
Run in this order; stop when time runs out.
```python
!python scripts/train.py --name iv_b --stage-a 2 --stage-b 4 --workers 4
!python scripts/train.py --name iv_a --stage-a 6 --stage-b 0 --workers 4
!python scripts/train.py --name iv_c --stage-a 2 --stage-b 4 --no-weights --workers 4
!python scripts/train.py --name iv_d --stage-a 2 --stage-b 4 --no-aug --workers 4
!python scripts/train.py --name v_b --stage-a 2 --stage-b 4 --backbone resnet50 --workers 4
```
(If ResNet50 runs out of GPU memory, add `--batch 32` and note it in `results/notes.md`.)

### Cell 7: pack the outputs for download
```python
!cd /kaggle/working && zip -qr lenscart_outputs.zip LensCart/results LensCart/models LensCart/prepared/split_final.csv runs/*/run.json runs/*/history.csv
!ls -lh /kaggle/working/*.zip
```
`LensCart/lenscart_resized_256.zip` (made in Cell 3) is the demo catalogue.

## Run it without keeping the tab open
Top right → **Save Version** → **Save & Run All (Commit)**. Kaggle runs every cell on its own
servers (up to 12 hours) and keeps everything in `/kaggle/working`. You can close the browser.
Check progress under the notebook's **Versions/Logs**.

Tip: run Cells 1–2 interactively first to confirm the paths print correctly, then Save & Run All.

## Getting the results to Vinay's laptop
Open the finished version → **Output** tab → download:
- `lenscart_outputs.zip` → unzip into `Desktop\LensCart\` (results/, models/, split_final.csv)
- `lenscart_resized_256.zip` → unzip into `Desktop\LensCart\data\` (gives `data/resized/`)

Large files (`models/best.pt`, `models/embeddings.npy`, zips) are never committed to git.

## Not covered yet
- FashionCLIP linear probe (Table V-c) and zero-shot (V-d): no script exists yet.
- M10 triplet and the robustness run: optional, after everything above.
