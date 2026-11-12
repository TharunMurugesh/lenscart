<?php
require __DIR__ . '/inc/layout.php';
$u = require_login();
$orders = orders_for_user((int) $u['id']);
page_header('My orders', 'account');
?>
<h1><?= icon('package') ?>My orders</h1>
<p class="sub">Signed in as <?= e($u['name']) ?> (<?= e($u['email']) ?>)</p>
<?php if (!$orders): ?>
  <p class="empty">No orders yet. <a href="index.php">Start shopping</a>.</p>
<?php endif; ?>
<?php foreach ($orders as $o): ?>
  <section class="card order">
    <div class="order-head">
      <b>Order #<?= (int) $o['id'] ?></b>
      <span class="sub"><?= e(date('j M Y, g:i a', strtotime($o['created_at']))) ?></span>
      <span class="tag status-<?= e($o['status']) ?>"><?= e(ucfirst($o['status'])) ?></span>
      <b class="push"><?= money($o['total']) ?></b>
    </div>
    <ul class="mini">
      <?php foreach (order_items((int) $o['id']) as $it): ?>
        <li><img src="<?= e($it['image']) ?>" alt=""><a href="product.php?id=<?= (int) $it['id'] ?>"><?= e($it['name']) ?></a><span>× <?= (int) $it['qty'] ?></span><b><?= money($it['qty'] * $it['price']) ?></b></li>
      <?php endforeach; ?>
    </ul>
  </section>
<?php endforeach; page_footer();
