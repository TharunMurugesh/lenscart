<?php
require __DIR__ . '/inc/layout.php';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    foreach ((array) ($_POST['qty'] ?? []) as $pid => $qty) cart_set((int) $pid, (int) $qty);
    if (isset($_POST['remove'])) cart_set((int) $_POST['remove'], 0);
    redirect('cart.php');
}
$items = products_by_ids(array_keys(cart()));
$total = 0;
page_header('Cart', 'cart');
?>
<h1><?= icon('shopping-cart') ?>Your cart</h1>
<?php if (!$items): ?>
  <p class="empty">Your cart is empty. <a href="index.php">Start shopping</a>.</p>
<?php else: ?>
<form method="post" class="card">
  <?= csrf_field() ?>
  <table class="table">
    <thead><tr><th colspan="2">Item</th><th>Price</th><th>Qty</th><th>Subtotal</th><th></th></tr></thead>
    <tbody>
    <?php foreach (cart() as $pid => $qty): if (!isset($items[$pid])) continue; $p = $items[$pid]; $total += $qty * $p['price']; ?>
      <tr>
        <td class="thumb"><img src="<?= e($p['image']) ?>" alt=""></td>
        <td><a href="product.php?id=<?= (int) $pid ?>"><?= e($p['name']) ?></a></td>
        <td><?= money($p['price']) ?></td>
        <td><input class="qtyin" type="number" name="qty[<?= (int) $pid ?>]" value="<?= (int) $qty ?>" min="0" max="10" aria-label="Quantity"></td>
        <td><?= money($qty * $p['price']) ?></td>
        <td><button class="icon-btn" name="remove" value="<?= (int) $pid ?>" title="Remove"><?= icon('trash-2') ?></button></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  <div class="cart-foot">
    <button class="btn ghost"><?= icon('check') ?>Update quantities</button>
    <div class="total">Total <b><?= money($total) ?></b></div>
    <a class="btn" href="checkout.php"><?= icon('arrow-right') ?>Checkout</a>
  </div>
</form>
<?php endif; page_footer();
