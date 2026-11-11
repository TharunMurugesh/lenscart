# LensCart — The Model

Tech-Bees Computer Vision 2026 · Presidency University · 12 Nov 2026 · 8:30 AM – 3:30 PM · LFL04
Platform: **web app**. The user **uploads** an image.

---

## The plan in one paragraph

We train our own computer vision model on a fashion dataset, build every part of the pipeline
below (M1 to M10), and write it up as a **research paper** with our own results. We don't compare
against other papers. We present what we built, how we built it, and what results we got, and the
judges verify it live by uploading images.

**The pitch line:** "We trained a computer vision model that looks at a clothing image and extracts
its features the way a fashion expert would: what it is, its colour, who it's for, and its style.
It also shows exactly where in the image it looked to decide."

---

## Dataset

**Fashion Product Images** (Kaggle, paramaggarwal).
- 44,416 products, Indian e-commerce (Myntra) product photos on white backgrounds.
- Labels per image: gender, masterCategory, subCategory, articleType, baseColour, season, year,
  usage, productDisplayName. *(Check the exact columns after download.)*
- **Full version:** 15.71 GB, images 1080×1440 or 1800×2400. **Recommended** (sharp Grad-CAM maps).
- **Small version:** about 300 MB, 80×60 images. Fallback if the download is too slow.
- Very unbalanced: 143 article types, from 7,065 T-shirts down to types with a single image.
- No pattern labels (floral, checked); M5 covers pattern.

---

## The pipeline

```
Uploaded image
  → M2  Clean-up: background removed, garment kept
  → M1  Our trained model: type, colour, gender, usage (with %)
  → M3  Heat maps: where the model looked for each answer
  → M7  True colour palette (k-means)
  → M5  Zero-shot extras: pattern, sleeve, neckline (CLIP)
  → Embedding (fingerprint vector)
        → M8  Position on the style map
        → Similar products from our catalogue
        → M9  "This, but in red"
  M4  Proof page · M6  Trained vs zero-shot · M10  Similarity-trained embeddings
```

---

## M1 to M10: everything we build

**M1. Multi-task attribute classifier: our own trained model**
- One shared backbone (EfficientNet or ResNet, pre-trained on ImageNet) with one head per question:
  articleType, baseColour, gender, usage (season optional).
- Transfer learning: train the heads with the backbone frozen first, then unfreeze the last block.
- Class-weighted loss for imbalance. Drop article types with too few images, and say so.
- **Result to show:** per-head accuracy, macro F1, confusion matrices.

**M2. Garment isolation (background removal)**
- `rembg` (U²-Net). On white catalogue backgrounds, a brightness threshold also works.
- **Result to show:** before/after image; the mask is also used for M3's focus score and M7.

**M3. Grad-CAM heat maps**
- A heat map for each head's answer (`pytorch-grad-cam`).
- **Garment-focus score:** share of the heat inside the garment mask (M2).
- **Result to show:** heat maps on test images and the judges' images; average focus score.

**M4. Proof page**
- Train/validation/test split, training curves, per-head and per-class accuracy, precision,
  recall, F1, confusion matrices.
- **Result to show:** the whole page, plus live Test mode (see below).

**M5. Zero-shot attributes with CLIP / FashionCLIP**
- Attributes we have no labels for: pattern (floral, checked, striped, solid), sleeve length,
  neckline. Text prompts, no training.
- **Result to show:** zero-shot answers with confidence. Spot-check accuracy on 50 images we label
  by hand.

**M6. Trained vs zero-shot benchmark (inside our own work)**
- On the same test set, for the attributes that have labels (type, colour): our M1 vs zero-shot
  CLIP.
- **Result to show:** one table. It answers "why train at all?"

**M7. True colour extraction (k-means)**
- k-means on the garment pixels only (M2 mask), giving dominant colours with hex codes and
  percentages.
- **Result to show:** colour swatches next to M1's colour answer.

**M8. Style map**
- Embeddings for the catalogue, squashed to 2D with UMAP. Points coloured by article type. The
  uploaded image appears as a new point.
- **Result to show:** the map, and how clusters form by type and usage. (Caveat: UMAP distorts
  large distances.)

**M9. "This, but in red" (text-edited search)**
- CLIP embedding arithmetic: image − text(current colour) + text(new colour) → nearest products.
- **Result to show:** live demo with 2–3 tested examples.

**M10. Similarity-trained embeddings (triplet loss)**
- Fine-tune the embedding with (anchor, positive, negative) triples. Positives: same articleType +
  colour; negatives: different type.
- **Result to show:** retrieval quality before vs after fine-tuning (e.g. how often the top-5
  results share the query's type and colour).
- **Highest risk.** Last in the build order.

### Optional experiment: robustness to real backgrounds
- Train a second version of M1 with background swap (garments pasted onto real backgrounds).
- Show real-photo accuracy and the garment-focus score for both versions.
- Only if M1–M9 are done. These are our own two runs, not a comparison with anyone else.

---

## Build order (if time runs out, stop at a tier boundary)

| Tier | Items | When |
|---|---|---|
| 1 | M1, M2, M3, M4 | Tonight (training) + morning |
| 2 | M5, M7, M8 | Morning |
| 3 | M6, M9 | Midday |
| 4 | M10, robustness experiment | Only if tiers 1–3 are done and rehearsed |

Anything not finished goes into the paper as **future work**. Never show half-working features.

---

## Proving the model: accuracy the judges can check

**Split before training:** train ~70% / validation ~15% / test ~15%, **stratified**, fixed random
seed, near-duplicates removed first. Every number shown comes from the test set only.

**Metrics:** accuracy, precision, recall, F1 (macro and weighted), confusion matrix, per head and
per class.

**Two accuracies, honestly labelled:**
1. **Test set:** catalogue images the model never saw.
2. **Real-world set:** 30–50 photos of the team's own clothes, labelled by us. This will be lower
   (domain shift). Show both and explain the gap.

**Live Test mode:** a button that shows a random unseen test image with its true label vs the
prediction, green or red, and a running score. Then judges upload their own images and check by
eye.

---

## The research paper (IEEE format, same pattern as our dropout paper)

Template: *Identifying Student Dropout Risk Among Academically Successful University Students*
(Sumanth, Sathvik, Sunny, Vinay, Mahesh). Same structure, tone and rigour.

**Title (draft):** *An Explainable Multi-Task Vision Model for Fashion Attribute Extraction from
Product Images*
**Authors:** team names, roll numbers, Department of CSE, Presidency University, Bengaluru.

**Abstract:** problem, dataset, method, and **real test numbers** (macro F1 per head, test size,
garment-focus score, real-photo accuracy), ending with an honest caution.
**Keywords:** computer vision, multi-task learning, fashion attributes, explainability, Grad-CAM,
zero-shot learning, class imbalance.

**I. Introduction**
- Context: fashion e-commerce needs structured attributes from images.
- Dataset in one paragraph.
- **Three numbered contributions**, e.g. (1) a multi-task model extracting type, colour, gender
  and usage from pixels alone; (2) explainability with Grad-CAM and a garment-focus score;
  (3) evaluation on both a held-out catalogue test set and real photos.
- Caveat sentence: Grad-CAM shows where evidence was found, not proof of reasoning.
- **Table I:** label columns, which became heads, which were dropped, and why.
- **Table II:** image counts: all → cleaned → after rare-class cut → train / val / test.
- **Fig. 1:** class distribution. **Fig. 2:** sample images per class.

**II. Literature Review**
- Paragraphs on: fashion classification on this dataset (PLOS ONE 2025, arXiv 2005.08170),
  Indian fashion (IndoFashion, CVPRW 2021), fine-grained attributes (Fashionpedia, DeepFashion,
  Flipkart CVPRW 2021), explainability (Grad-CAM), vision-language models (CLIP, FashionCLIP,
  2025–26 zero-shot attribute studies).
- **Table III:** Title / Technique / Gap relative to this study.
- Closing sentence in the template's style: *the gap is not a claim of higher accuracy than
  published systems, but a different task: image-only, multi-task, explainable extraction
  evaluated on real photos.*

**III. Methodology**
- Data cleaning: near-duplicate removal, rare-class threshold (stated), label merges if any.
- **Leakage-conscious pipeline:** split first (stratified, fixed seed); class weights and any
  statistics computed from training data only; test set used once.
- Preprocessing: resize/crop, normalisation, augmentation (mild colour jitter).
- Model: backbone + heads (diagram), loss (weighted cross-entropy), optimizer, learning rate,
  epochs, early stopping, hardware.
- Components M2–M10, one short paragraph each.
- **Primary metric justified:** macro F1, because classes are imbalanced and accuracy hides rare
  classes. Accuracy, precision and recall as secondary.
- 95% **bootstrap confidence intervals** (1,000 resamples of the test predictions).
- **Fig. 3:** pipeline diagram, numbered steps (like the template's Fig. 3).

**IV. Results**
- **Table IV, ablation:** our own variants (frozen vs fine-tuned, with/without background
  removal, with/without class weighting).
- **Table V, backbones:** e.g. ResNet50 vs EfficientNet vs FashionCLIP linear probe, plus M6
  (trained vs zero-shot).
- Selected model on the held-out test set, once, with confidence intervals.
- Confusion matrices and training curves (figures).
- **Table VI, retrieval:** top-1 / 3 / 5 / 10 results matching the query's type and colour, before
  and after M10 if built.
- Grad-CAM figures + garment-focus score (read "as approximate", like the template's permutation
  importance).
- **Table VII, audit:** performance by gender label, master category, and catalogue vs real
  photos. Small groups marked N/A.
- M5, M7, M8, M9 results as short subsections with a figure each.

**V. Conclusion and Future Scope**
- Summary with the key numbers.
- **Limitations, stated plainly:** single dataset, catalogue images (domain shift), small
  real-photo set, label noise (Kurta/Kurti), coarse heat maps, dataset gender labels.
- Future work: unfinished M items, detection for full-body photos, more real-world data.

**VI. References:** IEEE style with DOIs. Dataset, ResNet, EfficientNet, ViT, Grad-CAM, CLIP,
FashionCLIP, U²-Net, UMAP, focal loss, triplet loss, PLOS ONE 2025, IndoFashion, Fashionpedia,
DeepFashion, scikit-learn, PyTorch.

**Rules:**
- Every number comes from our own runs. No placeholder figures in the final copy.
- Every table in the paper is generated directly by the notebook.

---

## Demo script

| # | Screen | What we show |
|---|---|---|
| 1 | The data | Dataset, size, labels, class distribution, sample images |
| 2 | The split | Train/val/test sizes per class; why the test set is locked |
| 3 | Training | Loss and accuracy curves; why we stopped there |
| 4 | Scores | Per-head metrics, confusion matrices (M4) |
| 5 | Live Test mode | Random unseen images, true vs predicted, running score |
| 6 | Judge's upload | M2 → M1 → M3 → M7 → M5, step by step |
| 7 | Real-world accuracy | Our 30–50 photos vs the test set |
| 8 | Embeddings | Style map (M8), similar products, "this, but in red" (M9) |
| 9 | Benchmarks | M6 table; M10 before/after if built |
| 10 | Where it's used *(short)* | Similar products with price and "Add to cart", plus the analytics view (covers the brief's e-commerce + analytics wording) |

**The one moment to aim for:** a judge uploads their own image and the screen ends on the heat
map: "this is where our model looked to decide it's a kurta."

---

## Data decisions to get right tonight
- **Rare classes:** keep only article types with enough images; state the threshold.
- **Imbalance:** class-weighted loss; report macro F1, not only accuracy.
- **Leakage:** remove near-duplicate images before splitting.
- **Seed:** fixed, so every rerun gives the same split and numbers.
- **Colour augmentation:** keep it mild, or the colour labels become wrong.

---

## Similar products and analytics (covers the brief)
- **Similar products:** nearest neighbours by embedding in our own catalogue (offline, reliable).
  Optional extra: our features as search text to a shopping-search API. **Never send the raw image
  to an image-search API**, or our model is skipped.
- **Analytics:** catalogue breakdown by type, colour and usage (auto-tagged by M1), upload
  history, model metrics (M4), style map (M8).

---

## Hard judge questions: practise answering these without help
- *Did you train it, or use a pre-trained model?* Both, on purpose: transfer learning for M1 and
  M10; zero-shot CLIP only where no labels existed (M5). M6 shows why training helped.
- *What's your accuracy?* Give the real per-head numbers from M4. Never round up.
- *How do you know it's not cheating?* Grad-CAM (M3) and the garment-focus score.
- *Where does it fail?* Point at the confusion matrix and explain why.
- *Why is real-photo accuracy lower?* Domain shift: trained on catalogue images, tested in real
  rooms.
- *What would you do with more time?* Whatever we didn't finish from the build order, plus
  detection for full-body photos and more real-world test images.
- *Isn't this Google Lens?* Lens is a product. This is a model we trained, and we can show you
  exactly how it decides.

---

## Tonight
1. Ask the coordinators: is training and preparing data before the event allowed?
2. Start the full dataset download in Colab.
3. Colab notebook: clean-up, split, M1 training, M4 metrics, save model, catalogue embeddings.
4. Team: photograph and label 30–50 of your own clothes (varied rooms, lighting, hangers, bed).
5. Laptop test: M2 and M3 run on CPU for a single image.
6. Pick 3 test images and cache their full results.
