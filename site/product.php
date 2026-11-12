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
$similar = products_similar($p, 8);
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
  </div>
</article>

<section class="block">
  <h2><?= icon('shirt') ?>Similar items</h2>
  <p class="sub">Same type, closest in colour, gender and occasion.</p>
  <?php product_grid($similar, 'No similar items yet.'); ?>
</section>
<section class="block">
  <h2><?= icon('receipt') ?>Customers also bought</h2>
  <p class="sub">From real orders that included this item.</p>
  <?php product_grid($together, 'Nobody has ordered this together with other items yet.'); ?>
</section>
<?php page_footer();
