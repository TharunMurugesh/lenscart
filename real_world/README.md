# Real-world test photos

Photos of our own clothes, labelled by us. They measure how the model does outside the
catalogue (real rooms, real light). Expect lower accuracy than on the test set: the model was
trained on white-background product photos.

## How to photograph

- **One garment per photo.** Nothing else of note in the frame.
- **Vary the setting:** different rooms, lighting (daylight, tube light, evening), and
  surfaces (on a hanger, on a bed, on the floor, held up, worn).
- Fill most of the frame with the garment. Keep it in focus.
- JPG or PNG. Name files simply: `rw_001.jpg`, `rw_002.jpg`, ...
- Aim for 30 to 50 photos, spread across several article types.
- Put the photos in `real_world/images/`. **Do not commit them** (photos stay out of git).

## How to label

Copy `labels_template.csv` to `labels.csv` and add one row per photo. Use the class names
below **exactly** (same spelling and capitals). If a column truly does not fit (for example,
a colour not in the list, or a pattern-mixed garment), leave that cell empty: it is skipped
when scoring, the same way masked labels are skipped on the test set.

Example row: `rw_001.jpg,Tshirts,Navy Blue,Men,Casual`

### articleType (49)
Accessory Gift Set, Backpacks, Belts, Bra, Briefs, Capris, Caps, Casual Shoes, Clutches,
Cufflinks, Dresses, Dupatta, Earrings, Flats, Flip Flops, Formal Shoes, Handbags, Heels,
Innerwear Vests, Jackets, Jeans, Kurtas, Kurtis, Leggings, Necklace and Chains, Night suits,
Nightdress, Pendant, Ring, Sandals, Sarees, Scarves, Shirts, Shorts, Skirts, Socks,
Sports Shoes, Sunglasses, Sweaters, Sweatshirts, Ties, Tops, Track Pants, Trousers, Trunk,
Tshirts, Tunics, Wallets, Watches

### baseColour (18)
Beige, Black, Blue, Brown, Cream, Gold, Green, Grey, Maroon, Navy Blue, Olive, Orange, Pink,
Purple, Red, Silver, White, Yellow

(Multi-coloured items: leave baseColour empty; "Multi" is not a class.)

### gender (5)
Boys, Girls, Men, Unisex, Women

### usage (4)
Casual, Sports, Ethnic, Formal
