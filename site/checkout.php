<?php
require __DIR__ . '/inc/layout.php';
$u = require_login();
if (!cart()) redirect('cart.php');
$err = '';
$addr = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    $addr = trim((string) ($_POST['address'] ?? ''));
    if (mb_strlen($addr) < 10 || mb_strlen($addr) > 250) {
        $err = 'Please enter a delivery address (10 to 250 characters).';
    } else {
        try {
            $oid = order_create((int) $u['id'], cart(), $addr);
            cart_clear();
            flash("Order #$oid placed. Thank you!");
            redirect('account.php');
        } catch (RuntimeException $e) {
            $err = $e->getMessage();
        }
    }
}
$items = products_by_ids(array_keys(cart()));
$total = 0;
foreach (cart() as $pid => $qty) if (isset($items[$pid])) $total += $qty * $items[$pid]['price'];
page_header('Checkout', 'cart');
?>
<h1><?= icon('receipt') ?>Checkout</h1>
<div class="layout">
  <form method="post" class="card form">
    <?= csrf_field() ?>
    <?php if ($err): ?><div class="flash bad"><?= icon('circle-alert') ?><span><?= e($err) ?></span></div><?php endif; ?>
    <label>Deliver to<textarea name="address" rows="4" required minlength="10" maxlength="250" placeholder="House, street, city, PIN"><?= e($addr) ?></textarea></label>
    <p class="sub">Demo shop: no payment is taken.</p>
    <button class="btn"><?= icon('check') ?>Place order · <?= money($total) ?></button>
  </form>
  <div class="card">
    <h2>Order summary</h2>
    <ul class="mini">
      <?php foreach (cart() as $pid => $qty): if (!isset($items[$pid])) continue; ?>
        <li><img src="<?= e($items[$pid]['image']) ?>" alt=""><span><?= e($items[$pid]['name']) ?> × <?= (int) $qty ?></span><b><?= money($qty * $items[$pid]['price']) ?></b></li>
      <?php endforeach; ?>
    </ul>
  </div>
</div>
<?php page_footer();
