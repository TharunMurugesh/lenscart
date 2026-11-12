<?php
require __DIR__ . '/inc/layout.php';
$keys = ['q', 'articleType', 'baseColour', 'gender', 'usage', 'min', 'max', 'sort'];
$f = [];
foreach ($keys as $k) $f[$k] = trim((string) ($_GET[$k] ?? ''));
foreach (['min', 'max'] as $k) if ($f[$k] !== '' && !is_numeric($f[$k])) $f[$k] = '';
$per = 24;
$page = max(1, (int) ($_GET['page'] ?? 1));
$res = products_search($f, $per, ($page - 1) * $per);
$facets = ['articleType' => 'Type', 'baseColour' => 'Colour', 'gender' => 'Gender', 'usage' => 'Occasion'];
page_header('Search', 'search');
?>
<div class="layout">
  <form class="filters card" method="get">
    <h2><?= icon('sliders-horizontal') ?>Filters</h2>
    <label>Words<input name="q" value="<?= e($f['q']) ?>" placeholder="e.g. blue denim"></label>
    <?php foreach ($facets as $k => $label): ?>
      <label><?= $label ?>
        <select name="<?= $k ?>">
          <option value="">Any</option>
          <?php foreach (facet_values($k) as $v): ?><option <?= $f[$k] === $v ? 'selected' : '' ?>><?= e($v) ?></option><?php endforeach; ?>
        </select>
      </label>
    <?php endforeach; ?>
    <div class="two">
      <label>Min ₹<input name="min" type="number" min="0" value="<?= e($f['min']) ?>"></label>
      <label>Max ₹<input name="max" type="number" min="0" value="<?= e($f['max']) ?>"></label>
    </div>
    <label>Sort
      <select name="sort">
        <?php foreach (['' => 'Name', 'price_asc' => 'Price: low to high', 'price_desc' => 'Price: high to low', 'new' => 'Newest'] as $v => $l): ?>
          <option value="<?= $v ?>" <?= $f['sort'] === $v ? 'selected' : '' ?>><?= $l ?></option>
        <?php endforeach; ?>
      </select>
    </label>
    <div class="row"><button class="btn"><?= icon('filter') ?>Apply</button><a class="btn ghost" href="search.php"><?= icon('x') ?>Clear</a></div>
  </form>
  <section>
    <p class="sub"><?= number_format($res['total']) ?> item<?= $res['total'] === 1 ? '' : 's' ?> found</p>
    <?php product_grid($res['rows'], 'No items match. Try fewer filters.'); ?>
    <?php pager($res['total'], $per, $page, array_filter($f, 'strlen')); ?>
  </section>
</div>
<?php page_footer();
