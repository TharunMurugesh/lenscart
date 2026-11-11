# An Explainable Multi-Task Vision Model for Fashion Attribute Extraction from Product Images

Vinay G | M Tharun
Roll Numbers: 20241CSE0759 | 20241CSE0692
Department of Computer Science and Engineering
Presidency University, Bengaluru, India

> Draft status: Sections I–III written. Abstract, Results (IV), Conclusion (V) and the final
> reference list wait for the training run. Every bracketed `[pending: ...]` marker is filled only
> from our own result files; every `[needs check]` marker is a citation detail to verify against
> the source before submission.

**Abstract.** [pending: written last, from results/test_metrics.csv, test_ci.csv and the
real-world set.]

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
| Validation and test after near-duplicate removal | [pending: results/notes.md] |

Fig. 1 shows the number of images per kept article type (prepared/fig1_article_types.png). The
largest kept type is T-shirts with 7,070 images and the smallest is cufflinks with 106, an
imbalance ratio of about 67 to 1. Fig. 2 shows sample images per class [pending: generated from
the resized images].

## II. Literature Review

Research relevant to this work covers garment classification on catalogue images, fine-grained
attribute datasets, explanation methods for convolutional networks, and vision-language models
that classify without task-specific training.

Several studies classify products in the same Fashion Product Images dataset, typically
predicting categories or article types with convolutional networks [3], [4] [needs check: confirm
the exact titles, authors, heads predicted and reported settings of the PLOS ONE 2025 article and
arXiv 2005.08170 before describing them in detail]. These works establish that catalogue images
carry enough signal for category prediction. The present study differs in predicting four
attributes jointly from one shared backbone and in attaching an explanation to each answer.

Rajput and Aneja introduced IndoFashion, a dataset of Indian ethnic garments, and showed that
ethnic wear such as kurtas, sarees and lehengas forms a distinct visual domain from Western
clothing [5]. Our data include ethnic article types (kurtas, kurtis, sarees, dupattas) inside a
general catalogue, and the usage head includes an Ethnic class.

DeepFashion [6] and Fashionpedia [7] provide large collections of fashion images with fine-grained
attribute and segmentation annotations, and have supported much of the work on clothing attribute
recognition. Attribute extraction for an Indian e-commerce catalogue was also studied at CVPR
workshops in 2021 [8] [needs check: confirm the Flipkart paper's title, authors and method]. These
resources focus on attribute vocabularies and annotation; our work focuses on a compact
four-head model whose answers are explained and checked against the garment region.

Grad-CAM [2] produces a class-specific heat map from the gradients flowing into the final
convolutional layer and is widely used to inspect what image regions support a prediction. We
use it per head, and add a quantitative check: the share of the heat that lies inside a garment
mask from U²-Net [9], a salient-object segmentation network.

CLIP [10] learns a joint embedding of images and text from image–caption pairs and can classify
images zero-shot by comparing an image with text prompts. FashionCLIP [11] adapts CLIP to the
fashion domain using product images and descriptions. Recent studies examine how well such models
recognise fashion attributes without training [12] [needs check: identify the specific 2025–26
zero-shot attribute study before citing]. We use FashionCLIP in two roles: for attributes with no
labels in our data (pattern, sleeve length, neckline), and as a zero-shot baseline against our
trained heads for the attributes that do have labels.

**TABLE III. SELECTED LITERATURE, TECHNIQUES AND GAPS RELATIVE TO THIS STUDY**

| Title | Technique | Gap relative to this study |
|---|---|---|
| Fashion Product Images classification studies [3], [4] | CNN classifiers on catalogue images | Usually single-task; explanation and real-photo evaluation not the focus [needs check] |
| IndoFashion [5] | Dataset and classifiers for Indian ethnic wear | Ethnic wear only; no multi-attribute heads |
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
are then detected with a perceptual hash: any validation or test image within a Hamming distance
of 4 of a training image is removed from validation or test (the training set is not changed)
[pending: count removed, from results/notes.md]. Class weights are computed from the training
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
precision is used on the GPU and the seed is fixed at 42 throughout. Hardware: [pending: from
results/notes.md].

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

**M10, similarity-trained embeddings** [pending: included only if built; otherwise moved to future
work].

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

[pending: training and evaluation.]

## V. Conclusion and Future Scope

[pending.]

## References

[1] P. Aggarwal, "Fashion Product Images Dataset," Kaggle. [needs check: exact citation form and year]
[2] R. R. Selvaraju, M. Cogswell, A. Das, R. Vedantam, D. Parikh, and D. Batra, "Grad-CAM: Visual explanations from deep networks via gradient-based localization," in Proc. IEEE ICCV, 2017.
[3] [needs check: PLOS ONE 2025 article on this dataset]
[4] [needs check: arXiv 2005.08170]
[5] P. S. Rajput and S. Aneja, "IndoFashion: Apparel classification for Indian ethnic clothes," in Proc. IEEE/CVF CVPR Workshops, 2021.
[6] Z. Liu, P. Luo, S. Qiu, X. Wang, and X. Tang, "DeepFashion: Powering robust clothes recognition and retrieval with rich annotations," in Proc. IEEE CVPR, 2016.
[7] M. Jia et al., "Fashionpedia: Ontology, segmentation, and an attribute localization dataset," in Proc. ECCV, 2020.
[8] [needs check: Flipkart CVPRW 2021 attribute extraction paper]
[9] X. Qin, Z. Zhang, C. Huang, M. Dehghan, O. R. Zaiane, and M. Jagersand, "U2-Net: Going deeper with nested U-structure for salient object detection," Pattern Recognition, vol. 106, 2020.
[10] A. Radford et al., "Learning transferable visual models from natural language supervision," in Proc. ICML, 2021.
[11] P. J. Chia et al., "Contrastive language and vision learning of general fashion concepts," Scientific Reports, 2022.
[12] [needs check: 2025–26 zero-shot fashion attribute study]
[13] M. Tan and Q. V. Le, "EfficientNet: Rethinking model scaling for convolutional neural networks," in Proc. ICML, 2019.
[14] L. McInnes, J. Healy, and J. Melville, "UMAP: Uniform manifold approximation and projection for dimension reduction," arXiv:1802.03426, 2018.

DOIs to be added for every reference before submission [needs check].
