<?php
require __DIR__ . '/inc/layout.php';
$u = current_user();
$mine = $u ? products_for_user((int) $u['id'], 8) : ['basis' => null, 'rows' => []];
$popular = products_popular(8);
$newest = products_newest(8);
page_header('Shop', 'shop');
?>
<section class="hero">
  <div class="hero-text">
    <h1>Fashion, understood from the photo</h1>
    <p>Snap or upload any clothing photo. Our trained vision model reads its type, colour, who it is for and the occasion, shows where it looked, and finds matching items in our store.</p>
    <div class="row">
      <a class="btn" href="photo.php"><?= icon('camera') ?>Search by photo</a>
      <a class="btn ghost" href="search.php"><?= icon('search') ?>Browse all</a>
    </div>
  </div>
  <div class="hero-pics">
    <?php foreach (array_slice($popular, 0, 4) as $p): ?>
      <a href="product.php?id=<?= (int) $p['id'] ?>"><img src="<?= e($p['image']) ?>" alt="<?= e($p['name']) ?>"></a>
    <?php endforeach; ?>
  </div>
</section>

<?php if ($mine['rows']): ?>
<section class="block">
  <h2><?= icon('sparkles') ?>Picked for you</h2>
  <p class="sub">Because you looked at <?= e($mine['basis']['baseColour']) ?> <?= e($mine['basis']['articleType']) ?> most.</p>
  <?php product_grid($mine['rows']); ?>
</section>
<?php endif; ?>

<section class="block">
  <h2><?= icon('flame') ?>Popular right now</h2>
  <p class="sub">Most ordered items<?= $u ? '' : '. Log in and browse for personal picks' ?>.</p>
  <?php product_grid($popular); ?>
</section>

<section class="block">
  <h2><?= icon('tag') ?>New in</h2>
  <?php product_grid($newest); ?>
</section>
<?php page_footer();
