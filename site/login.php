<?php
require __DIR__ . '/inc/layout.php';
$err = '';
$email = '';
$next = safe_next($_GET['next'] ?? $_POST['next'] ?? null);
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    $email = trim((string) ($_POST['email'] ?? ''));
    $u = filter_var($email, FILTER_VALIDATE_EMAIL) ? user_by_email($email) : null;
    if ($u && password_verify((string) ($_POST['password'] ?? ''), $u['password_hash'])) {
        login_user($u);
        redirect($u['role'] === 'admin' && $next === 'index.php' ? 'admin/dashboard.php' : $next);
    }
    $err = 'Email or password is wrong.';
}
page_header('Log in', 'login');
?>
<form method="post" class="card form narrow">
  <h1><?= icon('log-in') ?>Log in</h1>
  <?= csrf_field() ?>
  <input type="hidden" name="next" value="<?= e($next) ?>">
  <?php if ($err): ?><div class="flash bad"><?= icon('circle-alert') ?><span><?= e($err) ?></span></div><?php endif; ?>
  <label>Email<input type="email" name="email" required value="<?= e($email) ?>" autocomplete="email"></label>
  <label>Password<input type="password" name="password" required autocomplete="current-password"></label>
  <button class="btn"><?= icon('log-in') ?>Log in</button>
  <p class="sub">New here? <a href="register.php">Create an account</a></p>
</form>
<?php page_footer();
