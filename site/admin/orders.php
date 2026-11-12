<?php
$ROOT = '../';
require __DIR__ . '/../inc/layout.php';
require __DIR__ . '/_nav.php';
require_admin();
const STATUSES = ['placed', 'shipped', 'delivered', 'cancelled'];
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    order_set_status((int) ($_POST['id'] ?? 0), (string) ($_POST['status'] ?? ''));
    flash('Order #' . (int) $_POST['id'] . ' updated.');
    redirect('admin/orders.php?' . http_build_query(array_filter(['status' => $_GET['status'] ?? '', 'page' => $_GET['page'] ?? ''])));
}
$status = in_array($_GET['status'] ?? '', STATUSES, true) ? $_GET['status'] : '';
$per = 30;
$page = max(1, (int) ($_GET['page'] ?? 1));
$res = orders_admin_list($status, $per, ($page - 1) * $per);
page_header('Orders', 'admin');
admin_nav('orders');
?>
<nav class="subnav" aria-label="Filter by status">
  <a href="orders.php" class="<?= $status === '' ? 'on' : '' ?>">All</a>
  <?php foreach (STATUSES as $s): ?><a href="?status=<?= $s ?>" class="<?= $status === $s ? 'on' : '' ?>"><?= ucfirst($s) ?></a><?php endforeach; ?>
</nav>
<div class="card table-wrap">
  <table class="table">
    <thead><tr><th>Order</th><th class="hide-sm">Date</th><th>Customer</th><th class="hide-sm">Items</th><th>Total</th><th>Status</th></tr></thead>
    <tbody>
    <?php foreach ($res['rows'] as $o): ?>
      <tr>
        <td>#<?= (int) $o['id'] ?></td>
        <td class="hide-sm"><?= e(date('j M Y', strtotime($o['created_at']))) ?></td>
        <td><?= e($o['name']) ?><div class="sub" style="margin:0"><?= e($o['email']) ?></div></td>
        <td class="hide-sm"><?= (int) $o['items'] ?></td>
        <td><?= money($o['total']) ?></td>
        <td>
          <form method="post" class="row">
            <?= csrf_field() ?><input type="hidden" name="id" value="<?= (int) $o['id'] ?>">
            <select name="status" onchange="this.form.submit()" aria-label="Status">
              <?php foreach (STATUSES as $s): ?><option value="<?= $s ?>" <?= $o['status'] === $s ? 'selected' : '' ?>><?= ucfirst($s) ?></option><?php endforeach; ?>
            </select>
          </form>
        </td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
</div>
<?php pager($res['total'], $per, $page, $status ? ['status' => $status] : []); page_footer();
