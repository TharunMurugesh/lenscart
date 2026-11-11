# Training notes

## Machine
- Local PC: NVIDIA GeForce RTX 4050 Laptop GPU, 6 GB VRAM, 24 CPU threads, Python 3.12.
- Deviation: handoff section 3 asks for 8 GB+ VRAM to train locally. Tharun chose to train on this
  6 GB GPU anyway (EfficientNet-B0, batch 64, AMP fits). ResNet50 (V-b) falls back to batch 32 if
  batch 64 runs out of memory; recorded below if that happens.
- DataLoader: 8 workers.

## Implementation choices not fixed by the handoff
- Stage A (frozen backbone): backbone BatchNorm layers are kept in eval mode, so running
  statistics stay frozen too.
- Cosine decay in Stage B is stepped per epoch with T_max = the Stage B epoch budget.
- Early stopping counts Stage B epochs without a new best val score (best taken over all epochs).

## Dataset (section 4)
- Downloaded the full Kaggle dataset (23.1 GB zip), extracted, zip deleted.
- The archive contained a nested duplicate copy (`fashion-dataset/fashion-dataset/images`,
  44,441 jpg); it was deleted. Images used: `data/fashion-dataset/images` (44,441 jpg).
- 4 of the 40,410 ids in `prepared/split.csv` have no image and are dropped from all outputs
  (listed in `results/missing_images.csv`): 39401 (val, Jeans), 39403 (test, Shirts),
  39410 (train, Shirts), 39425 (train, Tshirts). So the train set loses 2 images because of
  missing files only; no other change to train.
- Tooling: kaggle CLI 2.2.5 imports `six` without declaring it; installed `six` manually.

## Near-duplicate removal (section 5) - rule changed, decided by Tharun
- Handoff rule as written: drop a val/test image if ANY train image has pHash Hamming <= 4.
  Result (kept for the record in `results/dropped_duplicates_phash_only.csv`,
  `results/preprocess_stats_phash_only.json`): 4,764 of 12,138 val/test images dropped
  (test 2,384, val 2,380). Of these, 0% shared a product name with the matched train image,
  only 26% had the same baseColour and 66% the same articleType (e.g. black handbag vs brown
  handbag of another brand; red vs blue T-shirt; sandals vs sports shoes). Formal Shoes,
  Cufflinks and Ties had 0 test images left, Sunglasses 1 of 160, 6 classes < 10.
  Cause: pHash is grayscale and 64-bit; catalogue photos on white with similar silhouettes
  collide.
- Rule used instead: drop a val/test image only if a train image with the SAME articleType
  AND baseColour is within pHash Hamming <= 4 (threshold unchanged). Train set unchanged.
- Result (`results/dropped_duplicates.csv`, `results/preprocess_stats.json`):
  2,468 dropped (test 1,262, val 1,206; Hamming 0: 266, 2: 905, 4: 1,297).
  Final split: train 28,270 / val 4,844 / test 4,824 (37,938 rows, after the 4 missing images).
- All 49 article types remain in test (smallest: Formal Shoes 10) and in val (smallest:
  Cufflinks 6; 3 classes < 10). Most thinned: Sunglasses (test 17 of 160), Formal Shoes
  (10 of 94), Ties (12 of 37) - many near-identical black items.
- `lenscart_resized_256.zip` contains all 40,406 resized images (including dropped duplicates),
  as the demo catalogue.
