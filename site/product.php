<?php
require __DIR__ . '/inc/layout.php';
$p = product_get((int) ($_GET['id'] ?? 0));
if (!$p) { http_response_code(404); page_header('Not found'); echo '<p class="empty">That product does not exist.</p>'; page_footer(); exit; }

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    $qty = max(1, min(10, (int) ($_POST['qty'] ?? 1)));
    if ($p['stock'] < 1) { flash('Sorry, this item is out of stock.', 'bad'); }
    else { cart_set((int) $p['id'], (cart()[$p['id']] ?? 0) + $qty); flash('Added to your cart.'); }
    redirect('product.php?id=' . (int) $p['id']);
}

$u = current_user();
if ($u) view_record((int) $u['id'], (int) $p['id']);
/* Similar items: visually nearest products (data/similar.json, made by scripts/build_catalog_embeddings.py
 * from the model's embeddings). Products without an embedding (added in the admin) fall back to tag rules. */
function visually_similar(int $id, int $limit): array {
    static $map = null;
    if ($map === null) {
        $f = __DIR__ . '/data/similar.json';
        $map = is_file($f) ? (json_decode((string) file_get_contents($f), true) ?: []) : [];
    }
    $ids = array_values(array_filter(array_map('intval', $map[(string) $id] ?? []), fn($x) => $x !== $id));
    if (!$ids) return [];
    $found = products_by_ids(array_slice($ids, 0, $limit + 4));
    $out = [];
    foreach ($ids as $x) { if (isset($found[$x])) $out[] = $found[$x]; if (count($out) >= $limit) break; }
    return $out;
}
$similar = visually_similar((int) $p['id'], 8);
$similarVisual = (bool) $similar;
if (!$similar) $similar = products_similar($p, 8);
$together = products_bought_together((int) $p['id'], 8);
page_header($p['name']);
?>
<article class="detail">
  <img class="detail-img card" src="<?= e($p['image']) ?>" alt="<?= e($p['name']) ?>">
  <div class="card detail-info">
    <h1><?= e($p['name']) ?></h1>
    <div class="price"><?= money($p['price']) ?></div>
    <div class="tags">
      <?php foreach (['articleType', 'baseColour', 'gender', 'usage'] as $k): if (!empty($p[$k])): ?>
        <a class="tag" href="search.php?<?= e(http_build_query([$k => $p[$k]])) ?>"><?= e($p[$k]) ?></a>
      <?php endif; endforeach; ?>
    </div>
    <p class="sub"><?= $p['stock'] > 0 ? (int) $p['stock'] . ' in stock' : 'Out of stock' ?> · <?= e($p['masterCategory']) ?><?= $p['subCategory'] ? ' / ' . e($p['subCategory']) : '' ?></p>
    <form method="post" class="row">
      <?= csrf_field() ?>
      <label class="qty">Qty <input type="number" name="qty" value="1" min="1" max="10"></label>
      <button class="btn" <?= $p['stock'] > 0 ? '' : 'disabled' ?>><?= icon('shopping-cart') ?>Add to cart</button>
    </form>

    <h2><?= icon('list') ?>Product details</h2>
    <dl class="specs">
      <?php foreach ([
          'Type' => $p['articleType'], 'Colour' => $p['baseColour'], 'For' => $p['gender'], 'Occasion' => $p['usage'],
          'Category' => $p['masterCategory'], 'Sub-category' => $p['subCategory'],
          'Availability' => $p['stock'] > 0 ? (int) $p['stock'] . ' in stock' : 'Out of stock', 'Product ID' => '#' . (int) $p['id'],
      ] as $k => $v): if ($v === null || $v === '') continue; ?>
        <dt><?= e($k) ?></dt><dd><?= e($v) ?></dd>
      <?php endforeach; ?>
    </dl>

    <section id="ai-card" class="ai-check" hidden>
      <h2><?= icon('scan-search') ?>What our AI sees in this photo</h2>
      <p class="sub">Our trained model reads the photo in your browser and is compared with the catalogue label.</p>
      <div class="ai-check-body">
        <div id="ai-heat"></div>
        <table class="table"><tbody id="ai-rows"></tbody></table>
      </div>
    </section>
  </div>
</article>

<section class="block">
  <h2><?= icon('shirt') ?>Similar items</h2>
  <p class="sub"><?= $similarVisual ? 'The items that look most alike to our model (its visual fingerprint of each photo).' : 'Same type, closest in colour, gender and occasion.' ?></p>
  <?php product_grid($similar, 'No similar items yet.'); ?>
</section>
<section class="block">
  <h2><?= icon('receipt') ?>Customers also bought</h2>
  <p class="sub">From real orders that included this item.</p>
  <?php product_grid($together, 'Nobody has ordered this together with other items yet.'); ?>
</section>

<script src="ai/vendor/ort.min.js"></script>
<script src="ai/lensai.js"></script>
<script>
/* Real model only: if it cannot load, the card stays hidden (no demo data on product pages). */
(async function () {
  const truth = <?= json_encode(['articleType' => $p['articleType'], 'baseColour' => $p['baseColour'], 'gender' => $p['gender'], 'usage' => $p['usage']]) ?>;
  const names = { articleType: "Type", baseColour: "Colour", gender: "For", usage: "Occasion" };
  const img = document.querySelector(".detail-img");
  try {
    if (!window.LensAI) return;
    await img.decode();
    const r = await LensAI.analyze(img);
    const esc = (s) => String(s).replace(/[&<>"']/g, (c) => "&#" + c.charCodeAt(0) + ";");
    document.getElementById("ai-rows").innerHTML = Object.keys(names).map((h) => {
      const got = r[h][0], same = got.label === truth[h];
      return `<tr class="${same ? "ok" : "no"}"><td>${names[h]}</td><td>${esc(got.label)} <span class="muted">${Math.round(got.p * 100)}%</span></td>
        <td class="muted">label: ${esc(truth[h] || "none")}</td><td>${same ? "&#10003;" : "&#10007;"}</td></tr>`;
    }).join("");
    const heat = r.heatmaps.articleType;
    heat.title = "Where the model looked to decide the type";
    document.getElementById("ai-heat").appendChild(heat);
    document.getElementById("ai-card").hidden = false;
  } catch (e) {
    console.warn("AI check skipped:", e);
  }
})();
</script>
<?php page_footer();
