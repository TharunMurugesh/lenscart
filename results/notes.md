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
