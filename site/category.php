<?php
/* Department landing page: category.php?c=men|women|kids|footwear|ethnic|sports|watches|accessories */
require_once __DIR__ . '/inc/layout.php';
require_once __DIR__ . '/inc/catalog.php';

$d = department((string) ($_GET['c'] ?? ''));
if (!$d) { http_response_code(404); page_header('Category not found'); echo '<p class="empty">That category does not exist. <a href="' . e(url('index.php')) . '">Back to the shop</a></p>'; page_footer(); exit; }

$types   = dept_types($d);
$colours = dept_colours($d);
$best    = dept_best_sellers($d, 12);
$new     = dept_products($d, 'new', 12);
$budget  = dept_products($d, 'price_asc', 12, 999);
$total   = dept_count($d);

function search_link(array $d, array $extra = []): string {
    return url('search.php?' . http_build_query($d['params'] + $extra));
}

function shelf(string $title, string $iconName, array $rows, string $more): void {
    if (!$rows) return; ?>
  <section class="c-shelf">
    <div class="c-shelf-h"><h2><?= icon($iconName) ?><?= e($title) ?></h2><a href="<?= e($more) ?>">View all <?= icon('arrow-right') ?></a></div>
    <div class="c-row"><?php foreach ($rows as $p) echo product_card($p); ?></div>
  </section>
<?php }

page_header($d['title'], 'cat-' . $d['slug']);
?>
<link rel="stylesheet" href="<?= url('css/catalog.css') ?>">

<nav class="c-crumbs" aria-label="Breadcrumb"><a href="<?= url('index.php') ?>">Shop</a><span>/</span><b><?= e($d['title']) ?></b></nav>

<section class="c-head">
  <div>
    <h1><?= e($d['title']) ?></h1>
    <p><?= e($d['blurb']) ?> · <?= number_format($total) ?> products</p>
  </div>
  <a class="c-photo" href="<?= url('photo.php') ?>"><?= icon('camera') ?><span>Have a photo? <b>Search by photo</b></span></a>
</section>

<?php if ($colours): ?>
<div class="c-chips" aria-label="Shop by colour">
  <?php foreach ($colours as $c): ?>
    <a class="c-chip" href="<?= e(search_link($d, ['baseColour' => $c['baseColour']])) ?>"><i style="--sw: <?= e(colour_hex($c['baseColour'])) ?>"></i><?= e($c['baseColour']) ?></a>
  <?php endforeach; ?>
  <a class="c-chip" href="<?= e(search_link($d, ['max' => 999])) ?>"><?= icon('tag') ?>Under ₹999</a>
</div>
<?php endif; ?>

<section class="c-shelf">
  <div class="c-shelf-h"><h2><?= icon('layers') ?>Shop by type</h2></div>
  <div class="c-types">
    <?php foreach ($types as $t): ?>
      <a class="c-type" href="<?= e(search_link($d, ['articleType' => $t['articleType']])) ?>">
        <img loading="lazy" src="<?= e(url($t['image'])) ?>" alt="<?= e($t['articleType']) ?>">
        <span><?= e($t['articleType']) ?></span><small><?= (int) $t['n'] ?> items</small>
      </a>
    <?php endforeach; ?>
  </div>
</section>

<?php
shelf('Best sellers', 'flame', $best, search_link($d));
shelf('New arrivals', 'sparkles', $new, search_link($d, ['sort' => 'new']));
shelf('Under ₹999', 'tag', $budget, search_link($d, ['max' => 999, 'sort' => 'price_asc']));
page_footer();

/** Swatch colour for a dataset colour name (display only). */
function colour_hex(string $name): string {
    static $m = ['Black' => '#1f1f1f', 'White' => '#ffffff', 'Blue' => '#2f5fb3', 'Brown' => '#7a4b2a', 'Grey' => '#8c8c8c',
        'Red' => '#c0392b', 'Green' => '#2e7d4f', 'Pink' => '#e8a0b4', 'Navy Blue' => '#1f2f5a', 'Purple' => '#6d4c9f',
        'Silver' => '#c0c0c0', 'Yellow' => '#e6c229', 'Beige' => '#d9c7a7', 'Gold' => '#c9a227', 'Maroon' => '#6b1f2a',
        'Orange' => '#e07b2c', 'Olive' => '#6b6b2a', 'Cream' => '#f2ead3'];
    return $m[$name] ?? '#cccccc';
}
