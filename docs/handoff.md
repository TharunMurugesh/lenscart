STATUS: waiting for the next Sara

# LensCart: training handoff

Written 2026-11-11, about 9 PM, for the session on Vinay's friend's PC.
**Your job: train and evaluate the model, and hand back the files listed in section 9.**
Everything is decided. If something is genuinely missing, follow the stated default and write it
down in `results/notes.md`; don't stop to ask. Only stop for the conditions in section 10.

Read this file fully first. Background (only if needed): `ideas.md` (the overall plan),
`concepts.md` (theory), `prepared/report.md` (data cleaning results).

---

## 1. Context in 60 seconds
- **Event:** Tech-Bees Computer Vision 2026, Presidency University. **12 Nov 2026, 8:30 AM.**
  Preparing in advance is allowed.
- **Team Code Explorers:** Vinay G (20241CSE0759), M Tharun (20241CSE0692).
- **What we pitch:** our own trained computer-vision model that reads a clothing image and
  outputs **article type, colour, gender and usage**, plus heat maps of where it looked. We show
  the judges the data, split, training, metrics and live predictions, and we write an IEEE-style
  research paper with our real numbers.
- **Division of work:** **you** = training and evaluation (this file). **Vinay's laptop** = web app,
  heat maps, colour extraction, zero-shot extras, style map, paper. His laptop has no NVIDIA GPU,
  so the final model must run on **CPU**.

## 2. What already exists in the repo
| Path | What it is |
|---|---|
| `scripts/prepare_data.py` | Cleans labels and makes the split. **Already run. Do not change the decisions in it.** |
| `prepared/split.csv` | **The split. Use it exactly.** One row per image: `id`, `split` (train/val/test), label names, and integer labels `y_articleType`, `y_baseColour`, `y_gender`, `y_usage`. **`-1` means "label unknown, skip in this head's loss".** |
| `prepared/label_maps.json` | Class name → index for each head. Ship it with the model. |
| `prepared/table1_labels.csv`, `table2_counts.csv`, `class_counts.csv`, `fig1_article_types.png`, `report.md` | Paper Tables I–II and Fig. 1 |

**Numbers:** 40,410 images · 49 article types (largest Tshirts 7,070, smallest Cufflinks 106) ·
18 colours (2,479 masked) · 5 genders · 4 usages (126 masked) · train 28,272 / val 6,051 /
test 6,087 · seed 42 · split is stratified by article type and grouped by product name (no product
name in both train and test).

## 3. Machine
1. Run `nvidia-smi`.
   - **NVIDIA GPU with 8 GB+ VRAM:** train locally on this PC.
   - **Otherwise:** use Google Colab (GPU runtime). Mount Google Drive and write every output and
     checkpoint to `/content/drive/MyDrive/LensCart/` so a disconnect loses nothing.
2. Python 3.10+. Install: `torch torchvision timm scikit-learn pandas numpy matplotlib pillow
   tqdm imagehash transformers kaggle` (CUDA build of torch on a local GPU).
3. Disk: about 50 GB free during download and unzip (23 GB zip + extracted images). Delete the zip
   after extracting.

## 4. Get the dataset
- Dataset: https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-dataset
  (**full version, about 23 GB**, not "-small").
- **Kaggle token:** Vinay has it (new `KGAT_...` format). Get it from him privately.
  - Locally: set the environment variable `KAGGLE_API_TOKEN` in your shell (not in any file in the
    repo).
  - Colab: 🔑 Secrets → name `KAGGLE_API_TOKEN` → enable notebook access → read with
    `google.colab.userdata.get`.
  - **Never** print it, write it into code, or commit it.
- Download with the CLI: `kaggle datasets download paramaggarwal/fashion-product-images-dataset -p data`
  (update `kaggle` to the latest version first if it doesn't accept the new token), then unzip
  into `data/`. `data/` is git-ignored.
- Find the folder that contains the `<id>.jpg` files (the archive may contain a nested duplicate
  folder; use one, delete the other). Check that every `id` in `prepared/split.csv` has an image.
  If a few are missing, drop those rows **from all outputs** and record the count in
  `results/notes.md`.

## 5. Preprocess images once
- For every id in `split.csv`: open, convert to RGB, resize so the **longer side is 256 px**
  keeping aspect ratio, paste centred onto a **256×256 white** canvas, save as JPEG quality 90 to
  `data/resized/<id>.jpg`. Do this once; training reads only these files.
- **Near-duplicate check (paper Table II row):** compute a perceptual hash (`imagehash.phash`) for
  every resized image. For each **val or test** image whose hash is within Hamming distance **≤ 4**
  of any **train** image, **drop it from val/test** (not from train). Save the dropped ids to
  `results/dropped_duplicates.csv`, report the count in `results/notes.md`, and write the updated
  split to `prepared/split_final.csv` (same columns). **All evaluation uses `split_final.csv`.**
  Don't change the train set.
- Zip `data/resized/` as `lenscart_resized_256.zip`. **Vinay needs it for the demo catalogue.**

## 6. The main model (M1): exact settings
- **Backbone:** `timm` `efficientnet_b0`, ImageNet-pretrained (`pretrained=True`). It's the
  CPU-friendly choice for the demo.
- **Heads:** global-pooled features (1280-d) → `Dropout(0.2)` → one `Linear` per head:
  articleType 49, baseColour 18, gender 5, usage 4 (sizes from `label_maps.json`).
- **Input:** 224×224, ImageNet mean/std normalisation.
- **Train augmentation:** RandomResizedCrop(224, scale=(0.8, 1.0)), RandomHorizontalFlip,
  RandomRotation(10, fill white), ColorJitter(brightness=0.1, contrast=0.1). **No hue or
  saturation jitter** (it would make the colour labels wrong).
- **Val/test transform:** Resize(224) only (images are already square).
- **Loss:** sum over the 4 heads of `CrossEntropyLoss(weight=w_head, ignore_index=-1)`.
  Class weights are computed **from the train split only**: `w_c = 1/sqrt(count_c)`, normalised so
  the mean weight is 1.
- **Optimiser:** AdamW, weight decay 1e-4, batch size 64, mixed precision (AMP) on GPU, seed 42
  everywhere (python, numpy, torch, DataLoader workers).
- **Schedule:**
  - Stage A: backbone **frozen**, heads only, lr 1e-3, **3 epochs**.
  - Stage B: unfreeze the **whole backbone**, lr 1e-4 (heads 1e-3), cosine decay, **up to 15
    epochs**, **early stopping with patience 3** on the val score.
- **Val score** (for choosing the best epoch): the mean of the four heads' **macro F1** on val
  (masked labels ignored).
- **Checkpoint every epoch** (`last.pt`, with model, optimiser, epoch and history) and keep
  `best.pt` (best val score). Training must be **resumable** from `last.pt`.
- **Log per epoch** to `results/history.csv`: epoch, stage, train loss, val loss, val accuracy and
  val macro F1 per head, val score, seconds.

## 7. Evaluation (paper Results section)
**Run the test set exactly once, with `best.pt`, after all training and selection is finished.**
Everything is computed on `split_final.csv` test rows; masked labels are skipped per head.

1. `results/test_metrics.csv`: per head: accuracy, macro precision, macro recall, **macro F1**,
   weighted F1, top-3 accuracy (articleType and baseColour), n.
2. **95% bootstrap confidence intervals**: 1,000 resamples of the test predictions (seed 42) for
   accuracy and macro F1 per head → `results/test_ci.csv`.
3. `results/per_class_<head>.csv`: precision, recall, F1, support for every class.
4. Confusion matrices as PNG for each head (`results/cm_<head>.png`, normalised by row). For
   articleType also `results/top_confusions.csv`: the 15 most frequent wrong (true, predicted)
   pairs.
5. `results/curves.png`: train/val loss and val macro F1 per epoch (from history.csv).
6. **Audit (paper Table VII)** `results/audit.csv`: articleType accuracy and macro F1 broken down by
   gender and by masterCategory. Write `N/A` for groups with fewer than 30 test images.
7. `results/test_predictions.csv`: id, true and predicted label, and confidence for every head
   (Vinay's "live Test mode" uses this).

## 8. Comparison tables (paper Tables IV–V and M6)
These are **our own variants**, not comparisons with other papers. To save time, every run here
uses the **same settings as section 6 but at most 6 epochs total** (Stage A 2 epochs + Stage B up
to 4) and reports **val** macro F1 per head plus the mean. **Never use the test set for these.**

**Table IV, ablation** (EfficientNet-B0) → `results/table4_ablation.csv`:
| Run | Change from section 6 |
|---|---|
| IV-a | Frozen backbone only (Stage A for 6 epochs) |
| IV-b | Full settings (short schedule) |
| IV-c | No class weights |
| IV-d | No augmentation |

**Table V, backbones** → `results/table5_backbones.csv`:
| Run | Model |
|---|---|
| V-a | EfficientNet-B0 (= IV-b) |
| V-b | ResNet50 (`timm resnet50`), same heads and settings |
| V-c | **FashionCLIP linear probe**: frozen FashionCLIP image embeddings (`transformers` `CLIPModel` / `CLIPProcessor`, model id `patrickjohncyh/fashion-clip`) + one logistic-regression classifier per head, trained on train, scored on val |
| V-d | **FashionCLIP zero-shot (M6)**: no training. Prompts `"a photo of a {class}"` for articleType, `"a photo of a {colour} clothing item"` for colour, `"a photo of {men's / women's / boys' / girls' / unisex} clothing"` for gender, `"a photo of {casual / sports / ethnic / formal} wear"` for usage. Scored on val |

Also record training time per run and **CPU inference time per image** for V-a and V-b (batch 1,
average of 50 images, on any CPU) → `results/latency.csv`.

**Optional, only if everything above is done:**
- **M10 triplet fine-tuning:** fine-tune the EfficientNet embedding with triplet loss
  (positive = same articleType and colour, negative = different articleType, margin 0.2,
  3 epochs). Report top-1/5/10 retrieval precision (share of retrieved items with the same
  articleType, and with the same type and colour) on test-as-queries vs train-as-gallery, before
  and after → `results/table6_retrieval.csv`. Without M10, still produce the "before" row with
  the `best.pt` embeddings.
- **Robustness:** an extra EfficientNet run where each training image's white background is
  replaced by a random real photo (mask = pixels > 240 in all channels) with probability 0.5.
  Same short schedule; record val macro F1 → append to Table IV as IV-e.

## 9. What to hand back to Vinay
1. `best.pt`: **CPU-loadable state_dict** (`torch.save(model.state_dict())` after `.cpu()`), plus
   `model_config.json` (backbone name, head sizes, input size, mean/std, label_maps path).
2. `embeddings.npy` (float32, 1280-d pooled features from `best.pt` for **every** id in
   `split_final.csv`) + `embedding_ids.csv` (same order). Used for similar products and the style
   map.
3. `lenscart_resized_256.zip` (section 5).
4. Everything in `results/` and `prepared/split_final.csv`.

**How to deliver:**
- **Large files** (`best.pt`, `embeddings.npy`, the zip): upload to a Google Drive folder and send
  Vinay the link. **Never commit them.**
- **Code and small outputs** (`results/`, `prepared/split_final.csv`, scripts or notebook): commit to
  this repo (rules below). Ask Vinay before pushing.

## 10. Stop and contact Vinay only if
- Neither a local NVIDIA GPU nor a Colab GPU is available.
- The dataset can't be downloaded (token rejected, access denied).
- Validation macro F1 for articleType stays below 0.30 after Stage B (something is broken).
- It's past **4 AM** and section 7 isn't done. Then hand back whatever is finished, with the
  `best.pt` you have.

## 11. Priority if time runs short
1. Sections 4–7 (main model + test evaluation): **must have**.
2. Section 9 deliverables: **must have**.
3. Table V-c and V-d (FashionCLIP probe and zero-shot).
4. Table IV ablations, then V-b ResNet50.
5. Optional M10 and robustness.

## 12. Rules (Vinay's, non-negotiable)
- Every number reported must come from an actual run. Never estimate or round up. If a run
  fails, write that it failed.
- Never use the test set for choosing anything. One final test evaluation only.
- Never commit `data/`, images, model weights, embeddings, zips or any token. Stage files by
  explicit path; **never `git add -A`**.
- Commit messages: short, lowercase, about 50 characters, one change, human-sounding (e.g.
  `add training script`). **No Co-Authored-By trailer and no AI attribution anywhere** (commits,
  code comments, README, paper).
- Don't push, deploy or share anything publicly without Vinay's OK.
- Don't change the cleaning decisions or `prepared/split.csv`. The only allowed change is the
  near-duplicate removal into `split_final.csv`.
- Say "done, needs your check" rather than "fixed" or "works" for anything not verified by a run.
- When finished: replace this file's first line with `STATUS: training done <date>`, list what was
  delivered and anything that failed in `results/notes.md`, and tell Vinay.
