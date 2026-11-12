# LensCart

LensCart combines a fashion marketplace with a trained image model. The PHP shop lives in `site/`; its photo search and product recommendations use the EfficientNet-B0 model in the browser through ONNX Runtime Web. The model predicts article type, colour, gender, and occasion.

## Run the marketplace locally

1. Start Apache and MySQL in XAMPP.
2. Create the `lenscart` database, then import `site/sql/schema.sql` followed by `site/sql/seed.sql`.
3. Set the database values in `site/inc/config.php` for your local MySQL account.
4. Serve the `site/` folder from Apache (for example, `C:\xampp\htdocs\lenscart`) and open `http://localhost/lenscart/`.

The repository includes the sample catalogue images, model-page data, product embeddings, the PyTorch checkpoint at `models/best.pt`, and its browser-ready export at `site/ai/lensnet.onnx`. The separate Fashion Product Images dataset is not included.

## Model and shop assets

The in-browser model and class labels are in `site/ai/`. The model results page reads `site/data/model_report.json`; catalogue pages and photo search use the generated files in `site/img/`, `site/ai/catalog_*`, and `site/data/similar.json`.

Python build scripts are in `scripts/`. `scripts/export_onnx.py` exports the checkpoint and checks the ONNX outputs against PyTorch. The catalogue builder expects a local MySQL database seeded with the shop products. See [site/README.md](site/README.md) for XAMPP, web-host, and demo-data details.
