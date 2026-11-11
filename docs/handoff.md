STATUS: waiting for the next Sara

# LensCart: handoff (written 2026-11-11, evening)

This note is self-contained. Read it in full, then read `ideas.md` (the plan) and `concepts.md`
(the study guide). Do not re-derive decisions listed here: Vinay has made them.

## The event
- **Tech-Bees Computer Vision 2026**, Presidency University, Bengaluru.
- **12 Nov 2026, 8:30 AM – 3:30 PM**, venue LFL04. Brief: "AI-powered online e-commerce platform
  with intelligent shopping features and integrated data analytics", web technologies.
- **Team Code Explorers:** Vinay G (20241CSE0759), M Tharun (20241CSE0692).
- Preparing before the event (data, training) is **allowed** (Vinay confirmed).

## Decisions already made (don't reopen)
1. **Pitch the trained model, not the app.** Anything framed as "upload a photo, find similar
   products" gets dismissed as Google Lens. The demo walks the judges through the model: data →
   split → training → metrics → live test → judge's own upload → heat maps.
2. **Build M1 to M10** from `ideas.md`, in the tiered build order. Unfinished items become future
   work in the paper. Never demo something half-working.
3. **No accuracy comparison against other papers.** Prior work appears only in the paper's
   literature review, framed as "a different task, not a claim of higher accuracy".
4. **Write an IEEE research paper** following the exact pattern of Vinay's earlier paper,
   *Identifying Student Dropout Risk Among Academically Successful University Students* (outline in
   `ideas.md`, "The research paper"). Every number comes from real runs; every table is generated
   by code.
5. **Web app** (not mobile). Users **upload** images (no camera).
6. **Dataset:** Kaggle *Fashion Product Images Dataset* (full version, about 15.7 GB, 44k
   products):
   https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-dataset
   Unzip into `data/` at the repo root (git-ignored).

## Where training runs
- **Training runs on Google Colab (free GPU)**, whichever PC opens it. The dataset is downloaded
  inside Colab with the Kaggle API (Vinay uploads his own `kaggle.json` into Colab; never in chat
  or git).
- Colab free-tier catches: GPU not guaranteed at busy times; sessions disconnect when idle and
  have a maximum length; everything is wiped at the end. So **mount Google Drive, save
  checkpoints and outputs there every epoch, and make training resumable.**
- Vinay's laptop (i5-12450HX, 8 GB RAM, Intel Arc, **no NVIDIA/CUDA**) is for data prep on
  `styles.csv`, the web app and the live demo on **CPU**. Pick a backbone that runs fast enough on
  CPU (EfficientNet-B0 or ResNet50; test latency), and save weights so they load on CPU.

## State right now
- Done: research, idea, plan (`ideas.md`), concepts study guide (`concepts.md`), dataset chosen.
- **Not started:** any code. No data downloaded yet. No notebook or training script.

## What's next, in order
1. Write the Colab notebook (Drive mount, Kaggle download, resumable training).
2. Locally, download the full dataset into `data/` and confirm `styles.csv` columns (expected: id, gender,
   masterCategory, subCategory, articleType, baseColour, season, year, usage, productDisplayName).
   Some rows of styles.csv are known to be malformed: parse defensively.
3. **Data step (produces paper Tables I–II):** class distribution; drop article types below a
   stated threshold; near-duplicate check; **stratified train/val/test ~70/15/15, fixed seed**,
   saved as `split.csv` and committed (small file), so every machine uses the same split.
4. **Tier 1:** M1 multi-task model (type, colour, gender, usage; weighted cross-entropy; frozen
   then partially unfrozen backbone; early stopping on validation), M2 background removal,
   M3 Grad-CAM + garment-focus score, M4 metrics (macro F1 primary; accuracy, precision, recall,
   confusion matrices, 95% bootstrap CIs with 1,000 resamples). Test set used **once**.
5. Paper tables IV–V need a few short runs (ablations and backbones) on a fixed subset.
6. Save: trained weights, catalogue embeddings, all metrics as CSV/JSON, all figures as PNG.
   Commit code and small outputs, not the dataset or large weights (share weights via Drive or a
   release, ask Vinay).
7. Then tiers 2–4 and the web app (FastAPI backend + simple frontend), then the paper.

## Vinay's pending decisions
- Paper format: Word (IEEE template, like his last paper) or LaTeX.
- Team still needs to photograph and label 30–50 of their own clothes for the real-world test set.

## Hard rules (repeat to any helper session)
- Explain before doing anything that changes behaviour or is hard to reverse; Vinay decides.
- No pushing, deploying, sending messages or spending money without asking Vinay.
- Never `git add -A`; stage explicit paths. Never commit `data/`, model weights or secrets.
- Secrets (Kaggle token etc.) only in local files that are git-ignored. Never paste them in chat.
- Commit messages: short, lowercase, about 50 chars, human-sounding. **No Co-Authored-By trailer
  and no AI attribution anywhere.**
- Never claim something works without running it. Say "needs your test" when unverified.
- Every number in the paper and on screen must come from a real run.
