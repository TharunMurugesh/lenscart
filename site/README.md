# LensCart shop

A fashion store where a trained vision model reads clothing photos: search by photo, AI-filled
product details for the admin, and recommendations from browsing history. PHP + MySQL + plain
HTML/CSS/JS. The model runs in the visitor's browser (onnxruntime-web), so there is no Python
server.

## Run locally (XAMPP)

1. Start **Apache** and **MySQL** in the XAMPP Control Panel.
2. Create the database and load the data (from the repo root):
   ```
   C:\xampp\mysql\bin\mysql.exe -u root -e "CREATE DATABASE IF NOT EXISTS lenscart CHARACTER SET utf8mb4"
   C:\xampp\mysql\bin\mysql.exe -u root lenscart < site\sql\schema.sql
   C:\xampp\mysql\bin\mysql.exe -u root lenscart < site\sql\seed.sql
   ```
   (Or import the two files in phpMyAdmin, schema first.)
3. Put this folder under `C:\xampp\htdocs\lenscart` (a copy or a junction) and open
   http://localhost/lenscart/
4. The sample product, test, and model images and the generated model report are included in this
   repository. To rebuild the product images and seed data, run
   `.venv\Scripts\python scripts\build_site_data.py` (needs `data/resized/`).

## Web host

Upload the whole folder, create a MySQL database, import `sql/schema.sql` then `sql/seed.sql`,
and set the four values in `inc/config.php`. `img/products/` must be writable for admin uploads.
`inc/db.php` is the only file that talks to the database.

## Demo logins

Admin: `admin@lenscart.local`. The password is generated when the seed is built and saved to
`CREDENTIALS.local.txt` (not in git). Ask the team for it.

## Data

- **Products:** 1,500 items sampled from the Fashion Product Images dataset (Kaggle,
  paramaggarwal), stratified by article type so all 49 types the model knows appear (seed 42).
  Names, images, type, colour, gender and occasion are the dataset's own labels.
- **Synthetic (made up for the demo):** prices (a fixed range per article type), stock, the 30
  customers, 240 orders spread over the last 60 days, and their product views. Order dates are
  relative to the moment the SQL is imported.

## Pages

- `index.php` home: picks from your own views when logged in, popular items, new items
- `search.php` text search and filters (type, colour, gender, occasion, price)
- `product.php` details, similar items, "customers also bought" (from real order co-occurrence)
- `photo.php` search by photo: model tags + heat maps, then matching store items
- `cart.php`, `checkout.php`, `account.php`, `login.php`, `register.php`
- `admin/` dashboard (revenue per day, revenue by type, average order value, top products,
  low stock), products (add/edit, AI fills the tags from the photo), orders (status)

## Security basics

Passwords stored with `password_hash`; sessions with regenerated ids; CSRF token on every form;
prepared statements for every query; input validated on the server; uploads checked with
`getimagesize`, limited to JPG/PNG/WebP under 5 MB and saved under random names.

## Third-party files (in `vendor/`)

Chart.js 4.4.1 (MIT) and Lucide icons 0.460.0 (ISC), licences included.
