# LensCart — Concepts to Know Before the Judges

How to use this: read one section at a time, then explain it out loud **without looking**. If you
can't say it simply, read it again. Each concept has:
**What** (plain words) · **Analogy** · **In our project** · **Judge question → answer**.

Sections are ordered from basics to advanced. Sections 1–9 are must-know. 10–14 are what makes us
stand out. 15–17 are good to know.

---

## 1. How a computer sees an image

**Pixels and channels**
- **What:** an image is a grid of numbers. Each pixel has 3 numbers (Red, Green, Blue), each from 0
  to 255. A 224×224 colour image is 224 × 224 × 3 ≈ 150,000 numbers. A **tensor** is just this
  grid of numbers in the form a model takes as input.
- **In our project:** every uploaded image becomes a tensor before the model sees it.

**Resizing and normalisation**
- **What:** models expect a fixed size (e.g. 224×224), so every image is resized. Normalisation
  shifts the pixel values to the same range the model was originally trained on (using ImageNet's
  average and spread), so the model isn't confused by brighter or darker inputs.
- **Judge:** *"Your images are different sizes. How do you handle that?"* → Resize to 224×224
  (center crop), then normalise with ImageNet statistics, because our
  backbone was pre-trained on ImageNet.

---

## 2. Convolutional Neural Networks (CNNs)

**Convolution and filters**
- **What:** a filter is a small grid (e.g. 3×3) of learned numbers that slides across the image
  and responds strongly to one pattern, such as a vertical edge. The output is a **feature map**:
  where in the image that pattern appears.
- **Analogy:** a stencil slid over a page, lighting up wherever the page matches its shape.

**Layers build up meaning**
- **What:** early layers detect edges and colours; middle layers detect textures (stripes, floral
  print); deep layers detect parts and objects (collar, sleeve, a whole shirt).
- **In our project:** this is why a model trained on general photos already "knows" textures and
  shapes that are useful for clothing.

**Pooling**
- **What:** shrinks feature maps by keeping the strongest signal in each small area. It makes the
  model cheaper and less sensitive to small shifts in position.

- **Judge:** *"Why a CNN for this?"* → Clothing is recognised by local patterns (texture, edges,
  shapes), and CNNs are built to find local patterns anywhere in the image.

---

## 3. Backbones and architectures

**Backbone and head**
- **What:** the **backbone** is the big part that turns an image into a feature vector (it
  "sees"). The **head** is a small layer on top that turns those features into an answer (it
  "decides").
- **Analogy:** the backbone is the eye, the head is the expert who interprets what the eye sees.
- **In our project:** one backbone, several heads (type, colour, gender, usage). See section 6.

**ResNet (He et al., 2015)**
- **What:** a very deep CNN with **residual (skip) connections**: each block adds its input back to
  its output. This lets the training signal flow through many layers without fading away (the
  *vanishing gradient* problem). ResNet50 has 50 layers.
- **In our project:** a strong, well-understood choice for M1's backbone.

**EfficientNet**
- **What:** a CNN family that scales depth, width and image resolution together in a balanced way.
  It's accurate for its size, which is good for running on a laptop CPU.

**Vision Transformer (ViT, Dosovitskiy et al., 2020)**
- **What:** cuts the image into 16×16-pixel patches, treats them like words in a sentence, and uses
  **attention** (each patch decides how much to look at every other patch). It has fewer built-in
  assumptions than a CNN ("less inductive bias"), so it usually needs more data or pre-training.
- **Judge:** *"CNN or Transformer: which is better?"* → It depends on data size. CNNs assume local
  patterns matter, which helps with smaller datasets. ViTs learn those relationships themselves,
  which works better with lots of pre-training.

---

## 4. Pre-training and transfer learning

**ImageNet**
- **What:** a dataset of about 1.2 million labelled photos in 1,000 everyday classes (the standard
  ILSVRC-2012 version). Most backbones are first trained on it.

**Transfer learning**
- **What:** take a model already trained on a big general dataset and retrain it for our task.
  The general knowledge (edges, textures, shapes) carries over.
- **Analogy:** hiring an experienced photographer and teaching them fashion, instead of teaching
  someone who has never held a camera.
- **Why:** much less data and training time, and usually better accuracy than training from
  scratch.

**Feature extraction vs fine-tuning**
- **Feature extraction:** **freeze** the backbone (its weights don't change) and train only the new
  head. Fast, safe with little data.
- **Fine-tuning:** also unfreeze some or all backbone layers and train them with a small learning
  rate. Usually more accurate, with more risk of overfitting.
- **In our project:** start frozen, then unfreeze the last block.
- **Judge:** *"Did you train from scratch?"* → No, on purpose. We used transfer learning from
  ImageNet. Training from scratch on 44k images would be slower and less accurate.

---

## 5. How training works

- **Forward pass:** the image goes through the model and comes out as a prediction.
- **Softmax:** turns the head's raw scores into probabilities that add up to 100% (e.g. Kurta 94%,
  Kurti 4%, Shirt 2%).
- **Loss (cross-entropy):** one number for how wrong the prediction was. It's large when the model
  is confident and wrong, small when it's confident and right.
- **Backpropagation:** works out how much each weight contributed to the error.
- **Gradient descent:** nudges every weight a little in the direction that reduces the loss.
- **Learning rate:** the size of each nudge. Too big and training jumps around; too small and it
  barely moves.
- **Optimizer (Adam / AdamW):** a smarter way of nudging that adapts the step size for each weight.
- **Batch:** a group of images processed together before one update (e.g. 32).
- **Epoch:** one full pass over all the training images.
- **Early stopping:** stop when the validation score stops improving, before the model starts
  memorising.
- **Analogy:** learning to throw darts. Throw (forward pass), see how far off you were (loss),
  adjust your arm (backprop + gradient descent), repeat for many rounds (epochs).
- **Judge:** *"How did you decide when to stop training?"* → Early stopping on the validation set:
  we kept the version with the best validation score.

---

## 6. Multi-task learning (our core model, M1)

- **What:** one shared backbone with several heads, each answering a different question (type,
  colour, gender, usage). The total loss is the sum of each head's loss (optionally weighted).
- **Why it helps:** the tasks share useful knowledge. Learning "gender" and "type" together can
  help both. It's also cheaper: one backbone instead of four models.
- **Multi-class vs multi-label vs multi-output (know this distinction):**
  - **Multi-class:** pick exactly one answer from many (type = Kurta). Uses softmax.
  - **Multi-label:** any number of yes/no tags can be true at once (floral AND cotton AND
    sleeveless). Uses a sigmoid per tag.
  - **Multi-output / multi-task:** several separate questions, each multi-class. **That's ours.**
- **Risk:** one task can dominate training. Fix by weighting the losses.
- **Judge:** *"Why not four separate models?"* → One shared backbone learns general clothing
  features once; each head is tiny. It's faster, smaller, and the tasks help each other.

---

## 7. Data: splits, leakage, imbalance

**Train / validation / test**
- **Train:** the model learns from these.
- **Validation:** used during training to choose settings and when to stop.
- **Test:** locked away until the end. **The only honest score.**
- **Analogy:** practice questions, mock exam, final exam you've never seen.

**Stratified split**
- **What:** each class keeps the same proportion in all three sets, so rare classes appear in the
  test set too.

**Data leakage**
- **What:** information from the test set sneaking into training. Example: near-identical photos
  of the same design in both train and test. The score looks great but means nothing.
- **Judge:** *"How do you know your test score is real?"* → Locked test set, stratified split,
  near-duplicate check before splitting, fixed random seed.

**Class imbalance and the long tail**
- **What:** T-shirts have 7,065 images; some categories have 1. A lazy model just guesses the big
  classes. The "long tail" is the many rare classes.
- **Fixes:**
  - **Undersampling:** cut big classes down (e.g. to 250 per class).
  - **Oversampling:** repeat or augment rare classes.
  - **Class-weighted loss:** mistakes on rare classes cost more.
  - **Focal loss (Lin et al., 2017):** focuses training on hard examples the model keeps
    getting wrong.
  - **Hierarchical labels:** if unsure between Kurta and Kurti, still get "Topwear → Ethnic" right


**Label noise**
- **What:** wrong or inconsistent labels. Example: Kurtis vs Kurtas, which the 2025 paper says are
  essentially the same category. The model gets "punished" for confusing two classes that are
  really one.
- **Judge:** *"Your confusion matrix shows Kurta vs Kurti mistakes."* → Those are close to label
  noise: even the latest paper treats them as essentially the same class.

---

## 8. Metrics (know these cold)

- **Accuracy:** right answers ÷ all answers. **Misleading when classes are imbalanced.**
- **Precision:** of everything predicted "Kurta", how many were really kurtas? (Are our "yes"
  answers trustworthy?)
- **Recall:** of all real kurtas, how many did we find? (Did we miss any?)
- **F1 score:** one number balancing precision and recall (their harmonic mean).
- **Macro vs weighted average (important with imbalance):**
  - **Macro:** average the metric across classes equally. Rare classes count as much as T-shirts.
    **The honest one.**
  - **Weighted:** average weighted by class size. Dominated by big classes and flatters the model.
- **Confusion matrix:** a grid of true class (rows) vs predicted class (columns). The diagonal is
  correct; off-diagonal cells show exactly which classes get mixed up.
- **Top-k accuracy:** is the right answer in the model's top k guesses (e.g. top-3)?
- **Confidence and calibration:** a calibrated model that says "80% sure" is right about 80% of
  the time. Deep networks are often overconfident.
- **Analogy (precision vs recall):** a fishing net. Precision is how much of your catch is the fish
  you wanted. Recall is how many of the fish in the lake you caught.
- **Judge:** *"Accuracy is 90%. So what?"* → With imbalance, accuracy hides failures. Here's macro
  F1 and per-class recall, including the rare classes.

---

## 9. Overfitting and how to prevent it

- **Overfitting:** the model memorises the training images instead of learning general patterns.
  You can see it on the curves: training accuracy keeps rising while validation accuracy falls.
- **Underfitting:** the model is too simple or under-trained to learn the patterns at all.
- **Prevention:**
  - **Data augmentation:** random flips, crops, rotations, colour jitter, so the model sees
    endless variations. **Careful:** colour jitter can break the colour head (a navy shirt turned
    purple is still labelled navy). Keep colour changes mild, or apply them only for other heads.
  - **Dropout:** randomly switching off some neurons during training, so the model can't rely on
    any single one.
  - **Weight decay:** a penalty that keeps weights small and the model simpler.
  - **Early stopping:** see section 5.
- **Judge:** *"How do you know it's not overfitting?"* → Training and validation curves stay close,
  and we test on images the model never saw, including real photos.

---

## 10. Explainability: Grad-CAM (our wow moment, M3)

**Why explainability matters**
- Deep models are "black boxes". A correct answer can come from the wrong reason.

**Shortcut learning ("Clever Hans")**
- **What:** the model learns a cheat instead of the real pattern. Example: if every "watch" photo
  has a wrist and every "shirt" has a white background, the model may use the wrist or the
  background, not the object.
- **Analogy:** Clever Hans was a horse that seemed to do arithmetic but was really reading its
  trainer's body language.

**CAM and Grad-CAM (Selvaraju et al., 2017)**
- **What:** shows which regions of the image drove a decision. Grad-CAM takes the last
  convolutional layer's feature maps, uses the **gradient** of the chosen class score to work out
  how important each feature map is, takes a weighted sum, keeps only the positive part, and
  stretches it back over the image as a heat map.
- **Plain version:** "Which parts of the image, if they changed, would most change the answer
  'Kurta'?" Those glow.
- **Limits (say these yourself, before a judge does):**
  - It's **coarse**: the last conv layer is a small grid (e.g. 7×7), so the map is blurry.
  - It shows **correlation, not proof**: where the evidence was, not a full explanation.
  - It depends on which layer you pick.

**Garment-focus score (our metric)**
- **What:** the share of the Grad-CAM heat that falls **inside the garment mask** (from background
  removal). 100% means the model looked only at the clothing.
- **Judge:** *"How do you measure whether the model looks at the right place?"* → Garment-focus
  score: the Grad-CAM heat inside the segmentation mask divided by the total heat.

---

## 11. Segmentation and background removal (M2)

- **Classification vs detection vs segmentation:**
  - **Classification:** what is in the image? (one label for the whole image)
  - **Object detection:** what, and where? (a box around each object, e.g. YOLO)
  - **Segmentation:** which exact pixels belong to the object? (a pixel mask)
- **Background removal:** segmentation into just two classes: garment vs background.
- **U²-Net (Qin et al., 2020):** the model inside the `rembg` tool. It finds the most prominent
  object (called *salient object detection*).
- **Catalogue shortcut:** our dataset has white backgrounds, so a simple brightness threshold
  already gives a good mask. That makes background swap nearly free.
- **Judge:** *"Why remove the background?"* → So the model judges the garment, not the room. We
  can prove it helps with the garment-focus score.

---

## 12. Domain shift and generalisation

- **Domain shift:** the test images come from a different "world" than the training images. Our
  training images are clean catalogue shots; a judge's photo is taken in a room with different
  lighting. Accuracy drops.
- **Generalisation:** how well a model performs on data unlike what it trained on.
- **Domain adaptation:** techniques to close that gap.
- **Background swap (copy-paste augmentation):** cut the garment out and paste it onto random
  real backgrounds during training, so background can't be used as a shortcut.
- **Street-to-shop:** the known research problem of matching real-world clothing photos to shop
  catalogue photos. Ours is a version of it.
- **Judge:** *"Why is real-photo accuracy lower?"* → Domain shift: trained on clean catalogue
  photos, tested in real rooms. That's why we measure both and added background swap.

---

## 13. Embeddings and similarity search

- **Embedding (feature vector):** the list of numbers the backbone produces for an image (e.g. 512
  or 2,048 numbers). Similar-looking images get similar numbers.
- **Analogy:** a fingerprint, or GPS coordinates in "style space".
- **Cosine similarity:** measures how closely two vectors point in the same direction. 1 means
  identical direction, 0 means unrelated.
- **Nearest-neighbour search:** find the catalogue vectors closest to the query vector.
- **FAISS / pgvector:** tools that do this search fast, even over millions of vectors.
- **UMAP and t-SNE:** squash high-dimensional vectors down to 2D for a picture. **Caveat:** they
  keep local neighbours but distort large distances, so the space between clusters isn't
  meaningful. Say this if you show the style map.
- **Judge:** *"How does 'find similar' actually work?"* → Each image becomes an embedding; we
  return the catalogue items with the highest cosine similarity.

---

## 14. CLIP, vision-language models and zero-shot (M5, M6)

**Contrastive learning**
- **What:** training by comparison. Show the model pairs that match and pairs that don't; it learns
  to pull matching pairs together and push others apart.

**CLIP (Radford et al., OpenAI, 2021)**
- **What:** trained on about 400 million image–caption pairs from the internet with contrastive
  learning. Images and text end up in **one shared space**: a photo of a red dress lands near the
  text "a red dress".

**Zero-shot classification**
- **What:** classifying into categories the model was never explicitly trained on. Write each class
  as text ("a photo of a floral kurta", "a photo of a checked kurta") and pick the text closest to
  the image. No training examples needed.
- **Analogy:** a well-read person identifying a "mustard block-print kurta" from its description,
  without ever having been shown one.

**FashionCLIP**
- **What:** CLIP further trained on fashion products (about 800k items, per its authors), so it
  understands fashion terms better than general CLIP.

**Linear probe**
- **What:** freeze a pre-trained model, take its embeddings, and train only a simple linear
  classifier on top. A standard way to measure how good the embeddings are. Recent fashion-attribute
  papers use this as a baseline.

**Vision-language models (VLMs)**
- **What:** large models that take images and text and answer in text: GPT-4o, Gemini. Research in
  2025–2026 compares them against trained classifiers for fashion attributes.

**Trained vs zero-shot: the trade-off**
- **Trained:** more accurate on the exact labels it learned, needs labelled data, can't do new
  attributes.
- **Zero-shot:** flexible (any attribute you can write as text), needs no labels, usually less
  accurate on a specific task.
- **Judge:** *"Why train at all when CLIP exists?"* → Here's our benchmark (M6): trained vs
  zero-shot on the same test set. We use zero-shot only where no labels exist (pattern).

---

## 15. Multimodal fusion (background only)

- **Multimodal:** using more than one type of input, such as image + text.
- **Early fusion:** combine the inputs before modelling.
- **Late fusion:** process each input separately (ResNet for the image, BERT for the title), then
  combine their feature vectors (e.g. **concatenation** = putting the two vectors end to end).
  The 2025 paper found concatenation worked best.
- **BERT:** a pre-trained language model that turns text into vectors.
- **Why we're image-only:** a customer's uploaded photo has no product title, so a model that
  depends on the title can't be used for search by image.

---

## 16. Stretch concepts

**Metric learning and triplet loss (M10)**
- **What:** train embeddings directly for similarity using triples: an anchor image, a similar
  (positive) image and a different (negative) image. The loss pushes the anchor closer to the
  positive than to the negative by at least a margin.

**k-means colour extraction (M7)**
- **What:** treat each garment pixel as a point in colour space and group them into k clusters. The
  cluster centres are the dominant colours; the cluster sizes give the percentages.
- **Why also classic CV:** it shows we understand vision beyond deep learning, and it can check the
  colour head's answer.

**Embedding arithmetic ("this, but in red", M9)**
- **What:** in CLIP's shared space, image vector − text("navy") + text("red") moves the search
  towards red versions.

---

## 17. Running it and responsibility

- **Inference:** using the trained model to make predictions (as opposed to training it).
- **Latency:** time per prediction. A single image on a laptop CPU is usually fine for a demo;
  measure it tonight.
- **Model size:** the number of parameters (weights). ResNet50 has about 25 million.
- **Bias:** the dataset labels gender as Men / Women / Boys / Girls / Unisex. The model learns the
  catalogue's conventions, not anything about who should wear what. Say this if asked.
- **Dataset licence:** check the licence on the Kaggle page before claiming it's free to use.
- **Uploaded images:** processed for the demo, not stored, or stated clearly if they are.

---

## Rapid-fire practice: answer each in under 20 seconds

1. What's the difference between a backbone and a head?
2. Why transfer learning instead of training from scratch?
3. What's the difference between validation and test sets?
4. Why is accuracy misleading on this dataset?
5. Precision vs recall: explain with an example from our data.
6. What does a confusion matrix tell you that accuracy doesn't?
7. How does Grad-CAM work, in one sentence? What are its limits?
8. What is the garment-focus score?
9. What is domain shift, and how did you address it?
10. What does zero-shot mean? When did you use it, and why?
11. Multi-class vs multi-label: which is your model?
12. Walk us through M1 to M10 in two minutes.
13. How do you know your test score isn't inflated?
14. What would you do with more time?
    *(Detection for full-body photos, triplet-loss fine-tuning, more real-world test photos,
    Indian ethnic wear from IndoFashion.)*

---

## Key papers to name (author, year, one line)
- **ResNet:** He et al., 2015. Skip connections make very deep networks trainable.
- **ViT:** Dosovitskiy et al., 2020. Images as sequences of patches with attention.
- **Grad-CAM:** Selvaraju et al., 2017. Gradient-based heat maps of where the model looked.
- **CLIP:** Radford et al., 2021. Images and text in one space, enabling zero-shot.
- **U²-Net:** Qin et al., 2020. Salient object segmentation, used for background removal.
- **Focal loss:** Lin et al., 2017. Focus training on hard examples, helps with imbalance.
- **UMAP:** McInnes et al., 2018. 2D maps of high-dimensional embeddings.
- **Seo, Lee & Jang, PLOS ONE, 2025.** Latest paper on our dataset: ResNet50 + BERT, 37 categories.
- **Rajput & Aneja, CVPR Workshops, 2021.** IndoFashion: Indian ethnic wear, 88.43% best.
