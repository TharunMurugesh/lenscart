<?php
$ROOT = '../';
require __DIR__ . '/../inc/layout.php';
require __DIR__ . '/../inc/labels.php';
require __DIR__ . '/_nav.php';
require_admin();

const MASTER = ['Apparel', 'Footwear', 'Accessories'];
$id = (int) ($_GET['id'] ?? 0);
$p = $id ? product_get($id) : null;
if ($id && !$p) redirect('admin/products.php');
$d = $p ?: ['name' => '', 'articleType' => '', 'baseColour' => '', 'gender' => '', 'usage' => '', 'masterCategory' => 'Apparel',
            'subCategory' => '', 'price' => '', 'stock' => 10, 'image' => ''];
$errs = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    foreach (['name', 'articleType', 'baseColour', 'gender', 'usage', 'masterCategory', 'subCategory', 'price', 'stock'] as $k) {
        $d[$k] = trim((string) ($_POST[$k] ?? ''));
    }
    if (mb_strlen($d['name']) < 3 || mb_strlen($d['name']) > 200) $errs[] = 'Name must be 3 to 200 characters.';
    foreach (['articleType', 'baseColour', 'gender', 'usage'] as $k) {
        if (!in_array($d[$k], LABELS[$k], true)) $errs[] = "Choose a valid $k.";
    }
    if (!in_array($d['masterCategory'], MASTER, true)) $errs[] = 'Choose a valid category.';
    if (!is_numeric($d['price']) || $d['price'] <= 0 || $d['price'] > 1000000) $errs[] = 'Price must be a positive number.';
    if (!ctype_digit($d['stock']) || (int) $d['stock'] > 100000) $errs[] = 'Stock must be a whole number.';

    // image: optional on edit, required on add
    $f = $_FILES['image'] ?? null;
    if ($f && $f['error'] !== UPLOAD_ERR_NO_FILE) {
        $info = $f['error'] === UPLOAD_ERR_OK && $f['size'] <= 5 * 1024 * 1024 ? @getimagesize($f['tmp_name']) : false;
        $ext = $info ? ([IMAGETYPE_JPEG => 'jpg', IMAGETYPE_PNG => 'png', IMAGETYPE_WEBP => 'webp'][$info[2]] ?? null) : null;
        if (!$ext) $errs[] = 'Image must be a JPG, PNG or WebP under 5 MB.';
        elseif (!$errs) {
            $name = 'u_' . bin2hex(random_bytes(8)) . '.' . $ext;
            if (move_uploaded_file($f['tmp_name'], __DIR__ . '/../img/products/' . $name)) $d['image'] = 'img/products/' . $name;
            else $errs[] = 'Could not save the image (is img/products writable?).';
        }
    } elseif (!$p) {
        $errs[] = 'Please add a product photo.';
    }

    if (!$errs) {
        $d['price'] = (float) $d['price'];
        $d['stock'] = (int) $d['stock'];
        $d['subCategory'] = $d['subCategory'] !== '' ? $d['subCategory'] : null;
        $newId = product_save($d, $p ? $id : null);
        flash($p ? 'Product saved.' : "Product #$newId added.");
        redirect('admin/product_edit.php?id=' . $newId);
    }
}

function select_field(string $name, string $label, array $opts, string $val): void {
    echo '<label>' . e($label) . '<select name="' . e($name) . '" id="f-' . e($name) . '" required><option value="">Choose…</option>';
    foreach ($opts as $o) echo '<option' . ($o === $val ? ' selected' : '') . '>' . e($o) . '</option>';
    echo '</select></label>';
}

page_header($p ? 'Edit product' : 'Add product', 'admin');
admin_nav($p ? 'products' : 'add');
?>
<h1><?= icon($p ? 'pencil' : 'plus') ?><?= $p ? 'Edit product #' . (int) $id : 'Add product' ?></h1>
<?php foreach ($errs as $er): ?><div class="flash bad"><?= icon('circle-alert') ?><span><?= e($er) ?></span></div><?php endforeach; ?>

<form method="post" enctype="multipart/form-data" class="ai">
  <?= csrf_field() ?>
  <div class="card form">
    <label id="drop" class="drop">
      <input id="file" type="file" name="image" accept="image/jpeg,image/png,image/webp" hidden>
      <?= icon('image-up') ?>
      <b><?= $p ? 'Replace photo (optional)' : 'Add the product photo' ?></b>
      <span>The AI fills in type, colour, gender and occasion from it.</span>
    </label>
    <img id="preview" class="preview" alt="Product photo" <?= $d['image'] ? 'src="../' . e($d['image']) . '"' : 'hidden' ?>>
    <div id="ai-note" class="notice" hidden></div>
  </div>
  <div class="card form">
    <label>Name<input name="name" required minlength="3" maxlength="200" value="<?= e($d['name']) ?>"></label>
    <div class="two">
      <?php select_field('articleType', 'Type', LABELS['articleType'], (string) $d['articleType']); ?>
      <?php select_field('baseColour', 'Colour', LABELS['baseColour'], (string) $d['baseColour']); ?>
      <?php select_field('gender', 'Gender', LABELS['gender'], (string) $d['gender']); ?>
      <?php select_field('usage', 'Occasion', LABELS['usage'], (string) $d['usage']); ?>
      <?php select_field('masterCategory', 'Category', MASTER, (string) $d['masterCategory']); ?>
      <label>Sub-category<input name="subCategory" maxlength="40" value="<?= e($d['subCategory']) ?>" placeholder="e.g. Topwear"></label>
      <label>Price (₹)<input name="price" type="number" min="1" step="1" required value="<?= e($d['price']) ?>"></label>
      <label>Stock<input name="stock" type="number" min="0" step="1" required value="<?= e($d['stock']) ?>"></label>
    </div>
    <div class="row"><button class="btn"><?= icon('save') ?>Save product</button>
      <?php if ($p): ?><a class="btn ghost" href="../product.php?id=<?= (int) $id ?>"><?= icon('eye') ?>View in shop</a><?php endif; ?></div>
  </div>
</form>

<script src="../ai/vendor/ort.min.js"></script>
<script src="../ai/lensai.js"></script>
<script src="../js/ai-stub.js"></script>
<script>
(function () {
  const file = document.getElementById("file"), img = document.getElementById("preview"), note = document.getElementById("ai-note");
  const drop = document.getElementById("drop");
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", (e) => { if (e.dataTransfer.files[0]) { file.files = e.dataTransfer.files; file.dispatchEvent(new Event("change")); } });
  file.addEventListener("change", async () => {
    const f = file.files[0];
    if (!f) return;
    img.src = URL.createObjectURL(f); img.hidden = false;
    note.hidden = false; note.textContent = "Reading the photo…";
    await img.decode();
    let r;
    try { r = await LensAI.analyze(img); } catch (e) { r = await LensAIStub.analyze(img); }
    const filled = [];
    for (const h of ["articleType", "baseColour", "gender", "usage"]) {
      const sel = document.getElementById("f-" + h);
      sel.value = r[h][0].label;
      filled.push(`${r[h][0].label} (${Math.round(r[h][0].p * 100)}%)`);
    }
    note.textContent = (r.stub ? "Demo data (model file not loaded): " : "AI filled in: ") + filled.join(", ") + ". Check and correct before saving.";
  });
})();
</script>
<?php page_footer();
