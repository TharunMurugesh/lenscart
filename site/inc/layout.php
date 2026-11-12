<?php
/* Header, footer, icons and the product card shared by every page. */
require_once __DIR__ . '/auth.php';

/** Inline a Lucide icon from vendor/lucide/<name>.svg (ISC licence). */
function icon(string $name, string $cls = ''): string {
    static $cache = [];
    if (!preg_match('/^[a-z0-9-]+$/', $name)) return '';
    if (!isset($cache[$name])) {
        $f = __DIR__ . '/../vendor/lucide/' . $name . '.svg';
        $svg = is_file($f) ? file_get_contents($f) : '';
        $svg = preg_replace('/<!--.*?-->\s*/s', '', $svg);
        $cache[$name] = preg_replace('/\s+/', ' ', trim($svg));
    }
    return str_replace('class="lucide ', 'aria-hidden="true" class="icon ' . e($cls) . ' lucide ', $cache[$name]);
}

function page_header(string $title, string $active = ''): void {
    $u = current_user();
    $nav = [['index.php', 'Shop', 'store', 'shop'], ['search.php', 'Search', 'search', 'search'], ['photo.php', 'Search by photo', 'camera', 'photo'], ['model.php', 'Our AI model', 'brain-circuit', 'model']];
    if ($u && $u['role'] === 'admin') $nav[] = ['admin/dashboard.php', 'Admin', 'layout-dashboard', 'admin'];
    ?><!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= e($title) ?> · <?= SITE_NAME ?></title>
<link rel="stylesheet" href="<?= url('css/style.css') ?>">
</head>
<body>
<header class="top">
  <a class="brand" href="<?= url('index.php') ?>"><?= icon('scan-search') ?><span><?= SITE_NAME ?></span></a>
  <form class="topsearch" action="<?= url('search.php') ?>" method="get" role="search">
    <?= icon('search') ?><input name="q" placeholder="Search shirts, kurtas, watches…" aria-label="Search" value="<?= e($_GET['q'] ?? '') ?>">
  </form>
  <nav class="nav">
    <?php foreach ($nav as [$href, $label, $ic, $key]): ?>
      <a href="<?= url($href) ?>" class="<?= $active === $key ? 'on' : '' ?>" title="<?= e($label) ?>"><?= icon($ic) ?><span><?= e($label) ?></span></a>
    <?php endforeach; ?>
    <a href="<?= url('cart.php') ?>" class="<?= $active === 'cart' ? 'on' : '' ?>" title="Cart"><?= icon('shopping-cart') ?><span>Cart</span><?php if (cart_count()): ?><b class="badge"><?= cart_count() ?></b><?php endif; ?></a>
    <?php if ($u): ?>
      <a href="<?= url('account.php') ?>" class="<?= $active === 'account' ? 'on' : '' ?>" title="My orders"><?= icon('user') ?><span><?= e(explode(' ', $u['name'])[0]) ?></span></a>
      <a href="<?= url('logout.php') ?>" title="Log out"><?= icon('log-out') ?></a>
    <?php else: ?>
      <a href="<?= url('login.php') ?>" class="<?= $active === 'login' ? 'on' : '' ?>" title="Log in"><?= icon('log-in') ?><span>Log in</span></a>
    <?php endif; ?>
  </nav>
</header>
<main class="wrap">
<?php if ($f = flash()): ?><div class="flash <?= e($f[1]) ?>"><?= icon($f[1] === 'ok' ? 'circle-check' : 'circle-alert') ?><span><?= e($f[0]) ?></span></div><?php endif;
}

function page_footer(): void { ?>
</main>
<footer class="foot">
  <div><?= SITE_NAME ?> · Team Code Explorers · Tech-Bees Computer Vision 2026</div>
  <div>Product photos and labels: Fashion Product Images dataset (Kaggle). Prices and stock are demo data.</div>
  <div><b>AI tools used:</b> Claude (Anthropic) for coding assistance.</div>
</footer>
</body>
</html>
<?php }

function product_card(array $p, string $extra = ''): string {
    $out = $p['stock'] <= 0 ? '<span class="tag muted">Out of stock</span>' : '';
    return '<a class="pcard" href="' . url('product.php?id=' . (int) $p['id']) . '">'
        . '<img loading="lazy" src="' . e(url($p['image'])) . '" alt="' . e($p['name']) . '">'
        . '<div class="pc-body"><div class="pc-name">' . e($p['name']) . '</div>'
        . '<div class="pc-meta">' . e($p['articleType']) . ' · ' . e($p['baseColour'] ?? '') . '</div>'
        . '<div class="pc-foot"><b>' . money($p['price']) . '</b>' . $out . $extra . '</div></div></a>';
}

function product_grid(array $rows, string $empty = 'Nothing here yet.'): void {
    if (!$rows) { echo '<p class="empty">' . e($empty) . '</p>'; return; }
    echo '<div class="grid">';
    foreach ($rows as $p) echo product_card($p);
    echo '</div>';
}

function pager(int $total, int $per, int $page, array $params): void {
    $pages = (int) ceil($total / $per);
    if ($pages <= 1) return;
    echo '<nav class="pager">';
    foreach ([max(1, $page - 1) => 'Previous', min($pages, $page + 1) => 'Next'] as $n => $label) {
        $q = http_build_query(array_merge($params, ['page' => $n]));
        $dis = ($label === 'Previous' && $page === 1) || ($label === 'Next' && $page === $pages) ? ' aria-disabled="true" class="off"' : '';
        echo '<a href="?' . e($q) . '"' . $dis . '>' . $label . '</a>';
    }
    echo '<span>Page ' . $page . ' of ' . $pages . '</span></nav>';
}
