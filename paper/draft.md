# An Explainable Multi-Task Vision Model for Fashion Attribute Extraction from Product Images

Vinay G | M Tharun
Roll Numbers: 20241CSE0759 | 20241CSE0692
Department of Computer Science and Engineering
Presidency University, Bengaluru, India

> Draft status: Sections I–III written. Abstract, Results (IV), Conclusion (V) and the final
> reference list wait for the training run. Every bracketed `[pending: ...]` marker is filled only
> from our own result files; every `[needs check]` marker is a citation detail to verify against
> the source before submission.

**Abstract.** We present a multi-task computer-vision model that reads a single product image
and predicts four attributes at once: article type (49 classes), base colour (18), gender (5) and
usage (4), together with Grad-CAM heat maps showing where the model looked for each answer. An
ImageNet-pretrained EfficientNet-B0 with one linear head per attribute is fine-tuned on 28,270
images of the Fashion Product Images dataset, using a split grouped by product name and a
label-aware near-duplicate filter on validation and test. On 4,824 held-out test images the
model reaches macro F1 of 0.860 (95% CI 0.844–0.871) for article type, 0.640 (0.621–0.658) for
colour, 0.818 (0.792–0.841) for gender and 0.859 (0.845–0.873) for usage, with 98.6% top-3
article-type accuracy, while running at 15.7 ms per image on a laptop CPU. It outperforms a
fine-tuned ResNet50 and a FashionCLIP linear probe under the same validation protocol, and
FashionCLIP zero-shot prompts by 0.20 in mean macro F1. [pending: real-world set result.]

**Keywords.** computer vision, multi-task learning, fashion attributes, explainability, Grad-CAM,
zero-shot learning, class imbalance

---

## I. Introduction

Fashion e-commerce catalogues rely on structured product attributes such as garment type, colour,
target gender and occasion. These attributes drive search filters, recommendations and catalogue
analytics, yet they are usually entered by hand when a product is listed, and the entry can be
incomplete or inconsistent. A model that reads these attributes directly from the product image
can fill or check them, provided its answers can be trusted and inspected.

This work uses the public Fashion Product Images dataset [1], collected from an Indian fashion
e-commerce catalogue. Each record contains a product photograph on a plain background together
with catalogue labels: gender, master category, sub-category, article type, base colour, season,
year, usage and product display name. The dataset is strongly imbalanced: a few article types
such as T-shirts account for thousands of images, while many types have only a handful.

The study makes three contributions. First, it trains a single multi-task model that predicts
four attributes, namely article type, base colour, gender and usage, from the image pixels alone.
Second, it attaches an explanation to every prediction using Grad-CAM heat maps [2], and
summarises each map with a garment-focus score: the share of the heat that falls inside a
foreground mask produced by a separate background-removal model. Third, it evaluates the model
on a held-out catalogue test set that is used once, and separately on photographs of the team's
own clothes taken in ordinary rooms, so that the gap between catalogue and real-world performance
is measured rather than assumed. Grad-CAM shows where the evidence for a prediction was found in
the image; it is not proof of how the model reasoned, and the focus score is read as an
approximate indicator.

Table I lists the label columns in the supplied data and how each was used. Table II reports the
image counts at each stage of cleaning and the resulting split.

**TABLE I. LABEL COLUMNS IN THE SUPPLIED DATASET**

| Column | Distinct values (raw) | Role | Use in final model |
|---|---|---|---|
| articleType | 143 | Head | 108 types after category filter; 49 with ≥ 100 images kept, rarer rows dropped |
| baseColour | 47 | Head | 18 colours with ≥ 300 images, Multi excluded; 2,479 labels masked |
| gender | 5 | Head | All 5 values; 0 labels masked |
| usage | 9 | Head | Casual, Sports, Ethnic, Formal; 126 labels masked |
| masterCategory | 7 | Filter | Kept Apparel, Footwear, Accessories |
| subCategory | 45 | Not used | Kept for analysis only |
| season | 4 | Excluded | Not visible in an image |
| year | 13 | Excluded | Not visible in an image |
| productDisplayName | – | Grouping only | Groups duplicate listings in the split; never a model input |

**TABLE II. IMAGE COUNTS AND ANALYSIS SPLIT**

| Step | Images |
|---|---|
| All records in styles.csv | 44,446 |
| With an image entry | 44,446 |
| Unique product ids | 44,446 |
| Apparel, Footwear, Accessories only | 41,911 |
| Article types with ≥ 100 images | 40,410 |
| Train | 28,272 |
| Validation | 6,051 |
| Test | 6,087 |
| Missing image files (removed) | 4 |
| Validation after near-duplicate removal | 4,844 |
| Test after near-duplicate removal | 4,824 |

Fig. 1 shows the number of images per kept article type (prepared/fig1_article_types.png). The
largest kept type is T-shirts with 7,070 images and the smallest is cufflinks with 106, an
imbalance ratio of about 67 to 1. Fig. 2 shows one training image per article type (prepared/fig2_samples.png).

## II. Literature Review

Research relevant to this work covers garment classification on catalogue images, fine-grained
attribute datasets, explanation methods for convolutional networks, and vision-language models
that classify without task-specific training.

Several studies classify products in the same Fashion Product Images dataset. Seo et al. used the
full version of the dataset (44,416 items, 143 categories), kept the 37 categories with at least
250 items, sampled 250 items per class with a 7:1:2 split, and combined a ResNet50 image encoder
with a BERT text encoder over the product description; concatenation fusion gave their best
result [3]. Li studied neural networks for fashion image classification and visual search on the
same catalogue [4]. These works establish that catalogue images carry enough signal for category
prediction. The present study differs in using the image alone, predicting four attributes
jointly from one shared backbone, and attaching an explanation to each answer.

Rajput and Aneja introduced IndoFashion, a dataset of about 106,000 images of Indian ethnic
garments in 15 classes, with a best reported classification accuracy of 88.43 percent [5]. Our data include ethnic article types (kurtas, kurtis, sarees, dupattas) inside a
general catalogue, and the usage head includes an Ethnic class.

DeepFashion [6] and Fashionpedia [7] provide large collections of fashion images with fine-grained
attribute and segmentation annotations, and have supported much of the work on clothing attribute
recognition. Parekh et al. studied fine-grained visual attribute extraction from fashion wear for
an Indian e-commerce catalogue [8]. These
resources focus on attribute vocabularies and annotation; our work focuses on a compact
four-head model whose answers are explained and checked against the garment region.

Grad-CAM [2] produces a class-specific heat map from the gradients flowing into the final
convolutional layer and is widely used to inspect what image regions support a prediction. We
use it per head, and add a quantitative check: the share of the heat that lies inside a garment
mask from U²-Net [9], a salient-object segmentation network.

CLIP [10] learns a joint embedding of images and text from image–caption pairs and can classify
images zero-shot by comparing an image with text prompts. FashionCLIP [11] adapts CLIP to the
fashion domain using product images and descriptions. Recent studies evaluate how well
vision-language models label product and fashion attributes without task-specific training,
including a three-tier evaluation framework for zero-shot product attribute labelling [12] and a
zero-shot analysis of fine-grained fashion attributes with GPT-4o mini and Gemini 2.0 Flash [15].
We use FashionCLIP in two roles: for attributes with no
labels in our data (pattern, sleeve length, neckline), and as a zero-shot baseline against our
trained heads for the attributes that do have labels.

**TABLE III. SELECTED LITERATURE, TECHNIQUES AND GAPS RELATIVE TO THIS STUDY**

| Title | Technique | Gap relative to this study |
|---|---|---|
| Seo et al. (2025), ResNet-BERT multi-modal classification [3] | ResNet50 image + BERT text, concatenation fusion; 37 categories | Needs product text; single category task; no explanation or real-photo test |
| Li (2020), fashion classification and visual search [4] | Neural network classifiers and visual search on this catalogue | Explanation and real-photo evaluation not the focus [needs check] |
| IndoFashion (2021) [5] | Dataset and classifiers for 15 Indian ethnic wear classes | Ethnic wear only; single task |
| DeepFashion [6], Fashionpedia [7] | Large annotated attribute and segmentation datasets | Dataset resources; not a compact explained attribute model |
| Grad-CAM [2] | Gradient-weighted class activation maps | General method; no garment-focus measure |
| CLIP [10], FashionCLIP [11] | Zero-shot image–text matching | No task-specific training; used here as a baseline and for unlabelled attributes |

The gap addressed here is not a claim of higher accuracy than published systems, but a different
task: image-only, multi-task, explainable attribute extraction, evaluated on both held-out
catalogue images and real photographs.

## III. Methodology

### A. Data Cleaning

The catalogue file contains 44,446 records. Twenty-two rows had commas inside the product name
that broke the CSV format; these were repaired and none were dropped. Only the Apparel, Footwear
and Accessories master categories were kept (41,911 images). Article types with fewer than 100
images were dropped, leaving 49 types and 40,410 images. For the colour head, the 18 colours with
at least 300 images were kept and the "Multi" value was excluded; images with any other colour
keep their place in the data but their colour label is masked (2,479 labels). For the usage head,
the four values Casual, Sports, Ethnic and Formal were kept and 126 other labels were masked. A
masked label is ignored in that head's loss and metrics only; the image still trains the other
heads. Season and year were excluded because they are not visible in an image.

### B. Leakage-Conscious Split

The split is made before any training statistic is computed. Images are divided into training
(70 percent), validation (15 percent) and test (15 percent) sets, stratified by article type,
with a fixed random seed of 42. Listings that share a product display name are grouped so that
the same product never appears in both training and test; this was checked. Near-duplicate images
are then detected with a 64-bit perceptual hash. A validation or test image is removed if a
training image with the same article type and base colour lies within a Hamming distance of 4
(the training set is not changed); 2,468 images were removed (1,206 validation, 1,262 test).
The label condition was added after inspection: with the hash alone, 4,764 images matched, but
only 26 percent of those matches shared the training image's colour and 66 percent its article
type, because catalogue photographs of different products with similar silhouettes on a white
background produce near-identical grayscale hashes. The hash-only rule would also have removed
every test image of three classes. Four images listed in the metadata had no image file and
were dropped. Class weights are computed from the training
split only. The test set is evaluated once, after all model selection has been done on the
validation set.

### C. Preprocessing

Every image is resized so that its longer side is 256 pixels and centred on a 256 × 256 white
canvas, matching the catalogue background. The model input is 224 × 224, normalised with the
ImageNet mean and standard deviation. Training augmentation uses a random resized crop (scale 0.8
to 1.0), horizontal flip, rotation up to 10 degrees with white fill, and mild brightness and
contrast jitter of 0.1. Hue and saturation are never altered, because doing so would make the
colour labels wrong. Validation and test images are only resized.

### D. Model

The backbone is EfficientNet-B0 [13] pre-trained on ImageNet. Its global-pooled 1,280-dimensional
feature vector passes through dropout with probability 0.2 and then into four linear heads, one
per attribute: article type (49 classes), base colour (18), gender (5) and usage (4) (Fig. 3).

The loss is the sum over the four heads of a class-weighted cross-entropy that ignores masked
labels. For each head, the weight of class c is 1/√n_c, where n_c is the number of training images
of that class, normalised so that the mean weight is 1. This softens the dominance of large
classes without letting the rarest ones dominate.

Training uses AdamW with weight decay 1e-4 and batch size 64 in two stages. In Stage A the
backbone is frozen and only the heads are trained for 3 epochs at learning rate 1e-3. In Stage B
the whole backbone is unfrozen, with learning rate 1e-4 for the backbone and 1e-3 for the heads,
cosine decay, up to 15 epochs, and early stopping with patience 3. The validation score used to
choose the best epoch is the mean of the four heads' macro F1 on the validation set. Mixed
precision is used on the GPU and the seed is fixed at 42 throughout. Hardware: a laptop NVIDIA
GeForce RTX 4050 GPU with 6 GB of memory; training the final model took 1,232 seconds.

### E. Pipeline Components

**M2, garment isolation.** U²-Net [9], through the rembg library, produces a soft foreground mask
for each image. The mask is used to display the garment without its background, to compute the
garment-focus score and to restrict colour extraction to garment pixels.

**M3, Grad-CAM and garment-focus score.** For each head, Grad-CAM [2] is computed for the
predicted class at the last convolutional layer of the backbone, upsampled to the image
resolution, and overlaid on the image. The garment-focus score is the sum of the heat inside the
M2 mask divided by the total heat. As a reference, a heat map spread evenly over the image would
score the share of the image covered by the garment, so the score is reported next to that share.

**M5, zero-shot attributes.** FashionCLIP [11] compares the image embedding with text prompts for
pattern (for example floral, checked, striped, solid), sleeve length and neckline, attributes
that have no labels in the dataset. Answers are reported with their similarity-based confidence
and spot-checked by hand on a small sample [pending: sample size and agreement].

**M6, trained versus zero-shot.** For the labelled attributes, the trained heads are compared with
FashionCLIP zero-shot prompts on the same validation images, to show what task-specific training
adds.

**M7, colour palette.** k-means clustering with k = 5 on the garment pixels only gives the
dominant colours of the garment with hexadecimal codes and pixel shares, shown next to the
model's base-colour answer.

**M8, style map.** The 1,280-dimensional pooled features of every catalogue image are projected to
two dimensions with UMAP [14] and coloured by article type. An uploaded image is placed on the
same map. UMAP preserves local neighbourhoods better than large distances, so only clusters and
near neighbours are interpreted.

**M9, text-edited search.** A FashionCLIP image embedding is shifted by the difference between two
text embeddings (for example, from the current colour to a requested colour), and the nearest
catalogue products to the shifted vector are returned.

**M10, similarity-trained embeddings.** Not built in this work (see Section V); retrieval is
evaluated with the classifier's pooled features only (Table VI).

### F. Evaluation

Because the classes are imbalanced, the primary metric is macro F1, which weights every class
equally; accuracy alone would be dominated by the largest classes. Accuracy, macro precision,
macro recall and weighted F1 are reported as secondary metrics, with top-3 accuracy for article
type and colour. Per-class precision, recall and F1, and row-normalised confusion matrices, are
reported for every head. Uncertainty is expressed by 95 percent bootstrap confidence intervals
from 1,000 resamples of the test predictions (seed 42). An audit reports article-type accuracy
and macro F1 by gender label and by master category, marking groups with fewer than 30 test
images as not applicable. A separate real-world set of photographs of the team's own clothes,
labelled by the team, measures performance outside the catalogue domain.

Fig. 3. Pipeline: (1) upload, (2) M2 background removal, (3) M1 multi-task prediction, (4) M3
Grad-CAM per head with garment-focus score, (5) M7 colour palette, (6) M5 zero-shot attributes,
(7) embedding for M8 style map and M9 search. [pending: diagram]

## IV. Results

All numbers in this section come from single runs with seed 42. Model selection used the
validation set only; the test set was evaluated once, after all selection was complete.

### A. Training

The final model ran all 18 epochs (3 frozen, 15 fine-tuning); early stopping did not trigger.
The best validation score (mean macro F1 over the four heads) was 0.796 at epoch 15, which is
the model evaluated below (Fig. 4, results/curves.png).

### B. Test Performance

**TABLE III. TEST RESULTS OF THE FINAL MODEL (4,824 IMAGES; MASKED LABELS SKIPPED)**

| Head | n | Accuracy | Macro P | Macro R | Macro F1 (95% CI) | Weighted F1 | Top-3 acc. |
|---|---|---|---|---|---|---|---|
| Article type | 4,824 | 0.904 | 0.856 | 0.868 | 0.860 (0.844–0.871) | 0.903 | 0.986 |
| Base colour | 4,523 | 0.707 | 0.644 | 0.643 | 0.640 (0.621–0.658) | 0.708 | 0.923 |
| Gender | 4,824 | 0.931 | 0.796 | 0.846 | 0.818 (0.792–0.841) | 0.932 | – |
| Usage | 4,813 | 0.924 | 0.846 | 0.875 | 0.859 (0.845–0.873) | 0.924 | – |

Confidence intervals are the 2.5th and 97.5th percentiles over 1,000 bootstrap resamples of the
test predictions. Validation results for the same model are within 0.02 of the test results on
every head (results/val_metrics.csv), so model selection did not overfit the validation set.

Colour is the hardest attribute. Most errors are between neighbouring shades, and the correct
colour is among the top three answers for 92.3 percent of test images. The gap between gender
accuracy (0.931) and macro F1 (0.818) reflects the small Boys, Girls and Unisex classes. The
article types with the lowest test F1 are Tunics (0.31), Flats (0.38) and Kurtis (0.51). The most
frequent confusions are visually close pairs: T-shirts and tops (36 and 28 test images in the two
directions), sports and casual shoes (25), flats and heels (24) and kurtas and kurtis (10)
(results/top_confusions.csv, Fig. 5).

### C. Ablation and Backbone Comparison

Tables IV and V use a shorter schedule (2 frozen epochs plus up to 4 fine-tuning epochs) and
report validation macro F1, never test.

**TABLE IV. ABLATION (EFFICIENTNET-B0, VALIDATION MACRO F1)**

| Run | Change | Type | Colour | Gender | Usage | Mean |
|---|---|---|---|---|---|---|
| IV-a | Frozen backbone only | 0.818 | 0.507 | 0.732 | 0.802 | 0.715 |
| IV-b | Full settings | 0.835 | 0.642 | 0.796 | 0.841 | 0.778 |
| IV-c | No class weights | 0.838 | 0.639 | 0.780 | 0.835 | 0.773 |
| IV-d | No augmentation | 0.847 | 0.633 | 0.796 | 0.847 | 0.781 |

Fine-tuning the backbone gives the largest gain (+0.063 mean macro F1 over the frozen backbone),
mostly in colour (+0.135). Class weighting adds 0.005. Augmentation did not help within six
epochs (−0.002); its effect may need the full schedule, which we did not test.

**TABLE V. BACKBONES AND FASHIONCLIP (VALIDATION MACRO F1)**

| Run | Model | Type | Colour | Gender | Usage | Mean | CPU ms/image |
|---|---|---|---|---|---|---|---|
| V-a | EfficientNet-B0 (fine-tuned) | 0.835 | 0.642 | 0.796 | 0.841 | 0.778 | 15.7 |
| V-b | ResNet50 (fine-tuned) | 0.802 | 0.610 | 0.757 | 0.808 | 0.744 | 36.5 |
| V-c | FashionCLIP linear probe | 0.850 | 0.636 | 0.763 | 0.834 | 0.771 | – |
| V-d | FashionCLIP zero-shot (M6) | 0.716 | 0.594 | 0.476 | 0.517 | 0.576 | – |

CPU time is the forward pass at batch size 1, averaged over 50 images on a laptop Intel CPU.
EfficientNet-B0 is both more accurate and 2.3 times faster than ResNet50, with 4.1 M instead of
23.7 M parameters. A logistic-regression probe on frozen FashionCLIP features is competitive for
article type (0.850) but weaker for gender and usage. Zero-shot prompts without any training
reach 0.576 mean macro F1, 0.20 below the trained model; this is the gap that task-specific
training closes (M6).

### D. Retrieval with Pooled Features

**TABLE VI. RETRIEVAL PRECISION (4,824 TEST QUERIES, 28,270 TRAINING IMAGES AS GALLERY)**

| Embedding | P@1 type | P@5 type | P@10 type | P@1 type+colour | P@5 type+colour | P@10 type+colour |
|---|---|---|---|---|---|---|
| EfficientNet-B0 pooled features | 0.882 | 0.857 | 0.845 | 0.471 | 0.443 | 0.425 |

Nearest neighbours by cosine similarity usually share the article type but match the colour less
than half the time, consistent with colour being the weakest head.

### E. Audit

**TABLE VII. ARTICLE-TYPE RESULTS BY GROUP (TEST)**

| Group | n | Accuracy | Macro F1 |
|---|---|---|---|
| Gender: Men | 2,285 | 0.948 | 0.794 |
| Gender: Women | 2,124 | 0.854 | 0.795 |
| Gender: Unisex | 224 | 0.951 | 0.870 |
| Gender: Boys | 119 | 0.933 | 0.570 |
| Gender: Girls | 72 | 0.764 | 0.526 |
| Category: Accessories | 1,310 | 0.957 | 0.636 |
| Category: Apparel | 2,879 | 0.897 | 0.701 |
| Category: Footwear | 635 | 0.825 | 0.606 |

Accuracy is lowest for images labelled Girls (0.764) and for footwear (0.825). Macro F1 within
small groups averages over few images per class and is less stable than accuracy.

### F. Real-World Photographs

[pending: real-world set.]

## V. Conclusion and Future Scope

A single EfficientNet-B0 with four linear heads, fine-tuned on catalogue images, predicts article
type, colour, gender and usage with test macro F1 between 0.64 and 0.86, explains each answer with
a heat map, and runs in about 16 ms per image on a laptop CPU. Under the same validation protocol
it is more accurate than a fine-tuned ResNet50 and a FashionCLIP linear probe, and 0.20 above
zero-shot prompting. Careful splitting mattered: grouping by product name and a label-aware
near-duplicate filter keep the test set honest without removing whole classes.

The main limitations are colour, where neighbouring shades are confused, the small child and
unisex classes, and the domain gap between white-background catalogue images and real
photographs. Future work: training with background replacement for robustness to real scenes,
similarity-trained embeddings (triplet loss) for better same-colour retrieval, longer schedules
for the ablations, and colour labels defined on a perceptual colour space.

## References

[1] P. Aggarwal, "Fashion Product Images Dataset," Kaggle, 2019. [Online]. Available: https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-dataset
[2] R. R. Selvaraju, M. Cogswell, A. Das, R. Vedantam, D. Parikh, and D. Batra, "Grad-CAM: Visual explanations from deep networks via gradient-based localization," in Proc. IEEE ICCV, 2017.
[3] I.-J. Seo, Y.-H. Lee, and B. Jang, "Classification of fashion e-commerce products using ResNet-BERT multi-modal deep learning and transfer learning optimization," PLoS ONE, vol. 20, no. 5, e0324621, May 2025, doi: 10.1371/journal.pone.0324621.
[4] F. Li, "Neural networks for fashion image classification and visual search," arXiv:2005.08170, 2020.
[5] P. S. Rajput and S. Aneja, "IndoFashion: Apparel classification for Indian ethnic clothes," in Proc. IEEE/CVF CVPR Workshops, 2021, pp. 3935–3939, arXiv:2104.02830.
[6] Z. Liu, P. Luo, S. Qiu, X. Wang, and X. Tang, "DeepFashion: Powering robust clothes recognition and retrieval with rich annotations," in Proc. IEEE CVPR, 2016.
[7] M. Jia et al., "Fashionpedia: Ontology, segmentation, and an attribute localization dataset," in Proc. ECCV, 2020, arXiv:2004.12276.
[8] Parekh et al., "Fine-grained visual attribute extraction from fashion wear," in Proc. IEEE/CVF CVPR Workshops, 2021. [needs check: co-authors]
[9] X. Qin, Z. Zhang, C. Huang, M. Dehghan, O. R. Zaiane, and M. Jagersand, "U2-Net: Going deeper with nested U-structure for salient object detection," Pattern Recognition, vol. 106, 2020.
[10] A. Radford et al., "Learning transferable visual models from natural language supervision," in Proc. ICML, 2021.
[11] P. J. Chia et al., "Contrastive language and vision learning of general fashion concepts," Scientific Reports, 2022.
[12] "Zero-shot product attribute labeling with vision-language models: A three-tier evaluation framework," in Proc. IEEE/CVF WACV Workshops, 2026, arXiv:2601.15711. [needs check: authors]
[13] M. Tan and Q. V. Le, "EfficientNet: Rethinking model scaling for convolutional neural networks," in Proc. ICML, 2019.
[14] L. McInnes, J. Healy, and J. Melville, "UMAP: Uniform manifold approximation and projection for dimension reduction," arXiv:1802.03426, 2018.
[15] "Can GPT-4o mini and Gemini 2.0 Flash predict fine-grained fashion product attributes? A zero-shot analysis," arXiv:2507.09950, 2025. [needs check: authors]
[16] K. He, X. Zhang, S. Ren, and J. Sun, "Deep residual learning for image recognition," in Proc. IEEE CVPR, 2016.
[17] T.-Y. Lin, P. Goyal, R. Girshick, K. He, and P. Dollár, "Focal loss for dense object detection," in Proc. IEEE ICCV, 2017.

DOIs to be added for every reference before submission [needs check].
