<?php
$ROOT = '../';
require __DIR__ . '/../inc/layout.php';
require __DIR__ . '/_nav.php';
require_admin();
$q = trim((string) ($_GET['q'] ?? ''));
$per = 30;
$page = max(1, (int) ($_GET['page'] ?? 1));
$res = products_admin_list($q, $per, ($page - 1) * $per);
page_header('Products', 'admin');
admin_nav('products');
?>
<form class="row" method="get" style="margin-bottom:12px">
  <input name="q" value="<?= e($q) ?>" placeholder="Search by name or type" style="max-width:320px">
  <button class="btn ghost"><?= icon('search') ?>Search</button>
  <a class="btn" href="product_edit.php"><?= icon('plus') ?>Add product</a>
  <span class="sub" style="margin:0"><?= number_format($res['total']) ?> products</span>
</form>
<div class="card table-wrap">
  <table class="table">
    <thead><tr><th colspan="2">Product</th><th class="hide-sm">Type</th><th class="hide-sm">Colour</th><th>Price</th><th>Stock</th><th></th></tr></thead>
    <tbody>
    <?php foreach ($res['rows'] as $p): ?>
      <tr>
        <td class="thumb"><img src="../<?= e($p['image']) ?>" alt=""></td>
        <td><?= e($p['name']) ?> <span class="sub">#<?= (int) $p['id'] ?></span></td>
        <td class="hide-sm"><?= e($p['articleType']) ?></td>
        <td class="hide-sm"><?= e($p['baseColour']) ?></td>
        <td><?= money($p['price']) ?></td>
        <td><?= (int) $p['stock'] ?></td>
        <td><a class="icon-btn" href="product_edit.php?id=<?= (int) $p['id'] ?>" title="Edit"><?= icon('pencil') ?></a></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
</div>
<?php pager($res['total'], $per, $page, $q !== '' ? ['q' => $q] : []); page_footer();
