# LensCart: pitch and demo guide

For Vinay and Tharun. Rehearse it out loud twice, with a timer, before 9:40.

## How we are marked (official sheet)

| Phase | Item | Marks |
|---|---|---|
| 1 (XAMPP) | PPT presentation | 10 |
| 1 | Relevance of title | 5 |
| 1 | AI and data analytics embedded | 10 |
| 1 | Team work | 5 |
| 1 | Works locally on XAMPP | 20 |
| 2 (live) | Works on www.web-a2z.com | 30 |
| 2 | Overall project working | 20 |

So **70 of 100 marks are "it works"**. The demo is the pitch: click through the real thing, not
slides about it. Slides support; they don't lead. **Team work (5):** both of you speak and
both of you touch the laptop.

## The opening line (say it first, no story)

> "LensCart is an online fashion store whose own computer-vision model reads every product
> photo: what it is, its colour, who it's for and the occasion. It shows where in the photo it
> looked. Shoppers search by photo, sellers get products tagged automatically, and the store
> catches its own wrong labels."

Who pays, if asked or on slide 2: online fashion sellers and catalogue teams. Auto-tagging cuts
listing work.

## Who does what

- **Vinay:** opening, product story, the "caught a label error" moment, business, closing.
- **Tharun:** the model (data, split, training, results, comparisons). He trained it, so he
  answers training questions.
- Swap the laptop at the hand-off points below. Judges see two people who both know the system.

## The 6-minute flow

| Time | Who | Screen | What to say / do |
|---|---|---|---|
| 0:00 | Vinay | Slide 1 | Opening line (above). |
| 0:30 | Vinay | Slide 2 | Problem in 2 sentences + who pays. Hold the Flip Flops/Sandals example for the demo. |
| 1:00 | Vinay | **Live: home page** | "This is running on XAMPP." Category bar, open **Women**, then a product. 15 seconds, don't tour. |
| 1:20 | Vinay | **Live: Search by photo** | Upload **demo photo 1** (white sneaker, product-style). Point at the 4 answers, then the heat map: "orange is where it looked." Scroll: "visually similar items from our store." |
| 2:10 | Vinay | **Live: product #10768** | **The moment.** "The dataset labels this Flip Flops. Our model says Sandals, 100%. Look at it: it's a sandal. The model caught an error in the catalogue." |
| 2:40 | Vinay → Tharun | **Live: Admin → Add product** | Pick a photo, the 4 fields fill themselves. "Sellers check and save." Hand over. |
| 3:00 | Tharun | **Live: Our AI model page** | Tiles: "90.4% type, 93.1% gender, 92.4% usage on 4,824 photos it never saw. Colour is hardest at 70.7%." Press **Next random image** and **Run live** twice. |
| 3:45 | Tharun | Slides 5 + 8 | Data cleaning, no leakage, near-duplicates removed. "Every design choice was tested on validation, never test." |
| 4:30 | Vinay | **Live: Admin dashboard** | Revenue, orders, order value, customers, 30 days. "Seeded demo orders; new orders appear live." |
| 5:00 | Vinay | Slide 10 | Limits (say them yourselves), next steps, GitHub, AI-tools disclosure. |
| 5:30 | Both | | "Questions?" |

Phase 2 is the same demo on **www.web-a2z.com**: home → search by photo → product #10768 →
dashboard. Shorter, because they've seen the story.

## Demo photos: prepare before 9:40

Keep 3 photos in a folder on the desktop, already tested:
1. **White sneaker, side view, plain background** (the one that ranks white sneakers first).
2. **A navy or black T-shirt, front view.**
3. **A watch or handbag**, to show it isn't only clothes.

**Rule for the live moment:** one item, side or front view, plain background. The model learned
from product photos. A worn, top-down or cluttered photo confuses it (it guessed "Watches 27%" on
worn sneakers on grass). If a judge offers their own photo, say: *"Sure. It works best with one
item on a plain background, since it learned from catalogue photos."* If it struggles, that
**is** the answer to "what are the limits" (slide 10). Never argue with the screen.

**Don't use** product photos where the heat sits on the background (e.g. some jackets). Test
your 3 photos and look at the heat maps first.

## Hard questions: answer without notes

1. **"Isn't this Google Lens?"** Lens is a search product. This is a model we trained, inside a
   store, and it shows you where it looked. Lens sends shoppers away; this keeps them in the
   store and tags the store's own catalogue.
2. **"Did you train it, or use a pre-trained model?"** Both, on purpose. EfficientNet-B0 starts
   from ImageNet (general shapes and textures), and we fine-tuned it on 28,270 fashion photos
   with 4 heads. Slide 8: fine-tuning took the score from 0.715 to 0.778.
3. **"How do you know 90% is real?"** The test set was locked and used once. The split is grouped
   by product name, and 2,468 near-duplicate photos were removed from test. The 95% interval is
   89.5–91.1%.
4. **"Why macro F1?"** Classes are very unbalanced (T-shirts 7,070, cufflinks 106). Accuracy
   rewards guessing big classes; macro F1 weighs every class equally.
5. **"Why is colour only 70%?"** Shades overlap (navy vs black, grey vs silver), lighting changes
   colour, and two-tone clothes have no single answer. Its top-3 accuracy is 92.3%.
6. **"How does the heat map work?"** Each head is one linear layer on averaged features, so the
   score splits exactly into a contribution from each region of the image. We draw that map
   (class activation mapping).
7. **"How does 'similar items' work?"** The model turns each photo into 1,280 numbers. Similar
   looks give similar numbers, so we rank the store by cosine similarity. On test, the top 5
   results share the type 85.7% of the time.
8. **"Where does the model run?"** In the browser: exported to ONNX (16 MB), run by ONNX Runtime
   Web, about 0.2 s per photo. No Python server, which is why it runs on XAMPP and web-a2z.
9. **"Why EfficientNet and not ResNet50?"** Better score (0.778 vs 0.744), 6× fewer weights, and
   twice as fast on a CPU. That matters in a browser.
10. **"Is the data real?"** Photos and labels: the public Kaggle Fashion Product Images dataset.
    Prices, stock, users and orders are demo data, and the site says so.
11. **"Is it secure?"** Hashed passwords, CSRF tokens on every form, prepared SQL statements,
    validated uploads, admin pages blocked for customers. Uploaded photos never leave the
    browser.
12. **"How does it scale / make money?"** A store's catalogue is tagged once (fingerprints and
    tags are precomputed); search runs on the shopper's device, so server cost doesn't grow
    with searches. Sellers pay for auto-tagging and label checks.
13. **"Was this built today?"** Answer truthfully, matching what the coordinators said this
    morning. The model was trained on a public dataset; the store, the in-browser AI and the
    integration are our work. Rule 2: Claude was used for coding assistance, disclosed in the
    footer and on slide 10.

## Don'ts

- Don't open with a story or with "Imagine…".
- Don't read the slides. Point at the live screen.
- Don't say "nobody has done this". Say what we built and measured.
- Don't claim numbers you can't point to. Every number above is in `results/`.
- Don't let a struggling upload hang. Say the limit, switch to a prepared photo.
