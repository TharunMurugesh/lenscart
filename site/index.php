<?php
require __DIR__ . '/inc/layout.php';
$u = current_user();
$mine = $u ? products_for_user((int) $u['id'], 12) : ['basis' => null, 'rows' => []];
$popular = products_popular(12);
$ethnic = dept_products(department('ethnic'), 'new', 12);
$all = ['where' => '1=1'];
$budget = dept_products($all, 'new', 12, 999);
$newest = products_newest(12);
$covers = dept_covers();

function home_shelf(string $title, string $ic, array $rows, string $more, string $sub = ''): void {
    if (!$rows) return; ?>
  <section class="c-shelf">
    <div class="c-shelf-h"><h2><?= icon($ic) ?><?= e($title) ?></h2><a href="<?= e($more) ?>">View all <?= icon('arrow-right') ?></a></div>
    <?php if ($sub): ?><p class="sub"><?= e($sub) ?></p><?php endif; ?>
    <div class="c-row"><?php foreach ($rows as $p) echo product_card($p); ?></div>
  </section>
<?php }

page_header('Shop', 'shop');
?>
<section class="hero">
  <div class="hero-text">
    <h1>Fashion, understood from the photo</h1>
    <p>Snap or upload any clothing photo. Our trained vision model reads its type, colour, who it is for and the occasion, shows where it looked, and finds matching items in our store.</p>
    <div class="row">
      <a class="btn" href="photo.php"><?= icon('camera') ?>Search by photo</a>
      <a class="btn ghost" href="model.php"><?= icon('brain-circuit') ?>How the model works</a>
    </div>
  </div>
  <div class="hero-pics">
    <?php foreach (array_slice($popular, 0, 4) as $p): ?>
      <a href="product.php?id=<?= (int) $p['id'] ?>"><img src="<?= e($p['image']) ?>" alt="<?= e($p['name']) ?>"></a>
    <?php endforeach; ?>
  </div>
</section>

<section class="block">
  <h2><?= icon('store') ?>Shop by category</h2>
  <p class="sub">Eight departments, every item tagged by type, colour, gender and occasion.</p>
  <div class="tiles">
    <?php foreach (departments() as $slug => $d): ?>
      <a class="tile" href="category.php?c=<?= e($slug) ?>">
        <?php if (!empty($covers[$slug])): ?><img loading="lazy" src="<?= e($covers[$slug]) ?>" alt=""><?php endif; ?>
        <b><?= e($d['title']) ?></b><small><?= e($d['blurb']) ?></small>
      </a>
    <?php endforeach; ?>
  </div>
</section>

<?php if ($mine['rows']) home_shelf('Picked for you', 'sparkles', $mine['rows'],
    'search.php?' . http_build_query(['articleType' => $mine['basis']['articleType']]),
    'Because you looked at ' . $mine['basis']['baseColour'] . ' ' . $mine['basis']['articleType'] . ' most.'); ?>
<?php home_shelf('Trending now', 'flame', $popular, 'search.php', $u ? '' : 'Most ordered items. Log in and browse for personal picks.'); ?>
<?php home_shelf('Ethnic picks', 'sparkles', $ethnic, 'category.php?c=ethnic'); ?>
<?php home_shelf('Under ₹999', 'tag', $budget, 'search.php?max=999&sort=price_asc'); ?>
<?php home_shelf('New in', 'package', $newest, 'search.php?sort=new'); ?>
<?php page_footer();
