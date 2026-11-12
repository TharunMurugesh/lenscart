<?php
require __DIR__ . '/inc/layout.php';
$err = '';
$name = $email = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    csrf_check();
    $name = trim((string) ($_POST['name'] ?? ''));
    $email = trim((string) ($_POST['email'] ?? ''));
    $pw = (string) ($_POST['password'] ?? '');
    if (mb_strlen($name) < 2 || mb_strlen($name) > 80) $err = 'Please enter your name (2 to 80 characters).';
    elseif (!filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($email) > 190) $err = 'Please enter a valid email.';
    elseif (strlen($pw) < 8 || strlen($pw) > 72) $err = 'Password must be 8 to 72 characters.';
    elseif (user_by_email($email)) $err = 'An account with this email already exists. Try logging in.';
    else {
        $id = user_create($name, $email, password_hash($pw, PASSWORD_DEFAULT));
        login_user(['id' => $id]);
        flash('Welcome to LensCart, ' . $name . '!');
        redirect('index.php');
    }
}
page_header('Create account', 'login');
?>
<form method="post" class="card form narrow">
  <h1><?= icon('user-plus') ?>Create account</h1>
  <?= csrf_field() ?>
  <?php if ($err): ?><div class="flash bad"><?= icon('circle-alert') ?><span><?= e($err) ?></span></div><?php endif; ?>
  <label>Name<input name="name" required minlength="2" maxlength="80" value="<?= e($name) ?>" autocomplete="name"></label>
  <label>Email<input type="email" name="email" required maxlength="190" value="<?= e($email) ?>" autocomplete="email"></label>
  <label>Password<input type="password" name="password" required minlength="8" maxlength="72" autocomplete="new-password"></label>
  <button class="btn"><?= icon('user-plus') ?>Create account</button>
  <p class="sub">Already have one? <a href="login.php">Log in</a></p>
</form>
<?php page_footer();
