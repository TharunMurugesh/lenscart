# Data preparation report

- Rows in styles.csv: 44,446 (22 rows with commas in the product name repaired, none dropped).
- Kept after cleaning: 40,410 images, 49 article types.
- Largest / smallest kept article type: Tshirts (7,070) / Cufflinks (106), imbalance ratio 67:1.
- Colour head: 18 classes; usage head: 4; gender head: 5.
- Masked labels: {'articleType': 0, 'baseColour': 2479, 'gender': 0, 'usage': 126}.
- Split (seed 42, stratified by article type, grouped by product name): train 28,272, val 6,051, test 6,087.
- No product name appears in both train and test (checked).
- Image-level near-duplicate check still to do in Colab (needs the images).
