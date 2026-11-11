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

## Data loading on Windows
- First test run hung at the first validation pass: 8 persistent train workers + 8 val workers
  (17 processes, each loading torch's CUDA DLLs) exhausted the Windows page file
  (`WinError 1455`); a val worker died and the main process waited forever.
- Fix: 6 train workers + 2 val workers (handoff suggests ~8). evaluate/export use 8 workers in a
  single loader. No effect on results, only speed.

## Main model M1 (section 6) - all settings as specified
- Ran all 18 epochs (3 Stage A + 15 Stage B); early stopping (patience 3) did not trigger.
- Best epoch 15 (Stage B), val score 0.7960;
  val macro F1 at epoch 15: articleType 0.8521, baseColour 0.6477, gender 0.8287, usage 0.8556.
  Total training time 1,231.7 s on the RTX 4050.
- Per-epoch log: `results/history.csv`, curves: `results/curves.png`.

## Test evaluation (section 7) - run once with best.pt (epoch 15), 4,824 test images
| head | n | accuracy | macro F1 (95% CI) | weighted F1 | top-3 acc |
|---|---|---|---|---|---|
| articleType | 4,824 | 0.9036 | 0.8595 (0.8436-0.8709) | 0.9032 | 0.9861 |
| baseColour | 4,523 | 0.7066 | 0.6396 (0.6207-0.6583) | 0.7079 | 0.9231 |
| gender | 4,824 | 0.9310 | 0.8175 (0.7917-0.8411) | 0.9324 | - |
| usage | 4,813 | 0.9237 | 0.8590 (0.8449-0.8733) | 0.9242 | - |
- Weakest article types (test F1): Tunics 0.31, Flats 0.38, Kurtis 0.51. Top confusions:
  Tshirts<->Tops, Sports<->Casual Shoes, Flats<->Heels, Kurtas<->Kurtis.
- Audit (`audit.csv`): all groups have >= 30 test images, so no N/A. Girls is the weakest
  gender group (articleType acc 0.7639, n=72).

## Comparison runs (section 8) - val only, short schedule (2 A + 4 B epochs)
- Table IV (val macro F1 mean): IV-a frozen 0.7148, IV-b full 0.7782, IV-c no class weights
  0.7729, IV-d no augmentation 0.7805. Note: without augmentation the val mean is slightly
  higher (+0.0023) than with it in this 6-epoch setting; reported as measured.
- IV-e (background swap) NOT RUN: optional, and no folder of real background photos available.
- Table V (val macro F1 mean): V-a EfficientNet-B0 0.7782, V-b ResNet50 0.7441 (batch 64, no
  OOM, so the batch-32 fallback was not needed), V-c FashionCLIP linear probe 0.7707,
  V-d FashionCLIP zero-shot 0.5760.
- V-c `train_seconds` (8.0 s) is the logistic-regression fit only; extracting the FashionCLIP
  embeddings took a further 74 s (train) + 14 s (val).
- V-c/V-d first failed: transformers 5.22 returns an output object from
  `get_image_features`; fixed by using its `pooler_output` (checked to equal CLIP's own
  `image_embeds`/`text_embeds`), then rerun successfully.
- Latency (CPU, batch 1, mean of 50 val images after 5 warm-up, forward pass only, laptop
  Intel CPU, 16 threads): EfficientNet-B0 15.68 ms, ResNet50 36.48 ms.
- Table VI retrieval "before" row (test queries vs train gallery, best.pt embeddings):
  P@1/5/10 same type 0.8823/0.8572/0.8447; same type+colour 0.4714/0.4432/0.4246.
- M10 triplet fine-tuning NOT RUN (optional).

## Delivered
- `models/best.pt` (CPU state_dict, structure checked), `models/model_config.json` (backbone
  prefix and head key names), `models/label_maps.json`, `models/embeddings.npy` (37,938 x 1280,
  float32), `models/embedding_ids.csv`, `lenscart_resized_256.zip` - large files, not committed;
  still need uploading to Google Drive.
- Everything in `results/` and `prepared/split_final.csv` (committed).
