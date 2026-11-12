<?php
/* Sessions, login state, CSRF tokens, escaping and small helpers. */
require_once __DIR__ . '/db.php';

if (session_status() === PHP_SESSION_NONE) {
    session_set_cookie_params(['httponly' => true, 'samesite' => 'Lax']);
    session_start();
}
$ROOT = $ROOT ?? '';

function e($s): string { return htmlspecialchars((string) $s, ENT_QUOTES, 'UTF-8'); }
function money($v): string { return CURRENCY . number_format((float) $v, 0); }
function url(string $path = ''): string { global $ROOT; return $ROOT . $path; }
function redirect(string $path): void { header('Location: ' . url($path)); exit; }

function csrf_token(): string {
    if (empty($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(32));
    return $_SESSION['csrf'];
}
function csrf_field(): string { return '<input type="hidden" name="csrf" value="' . e(csrf_token()) . '">'; }
function csrf_check(): void {
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && !hash_equals($_SESSION['csrf'] ?? '', $_POST['csrf'] ?? '')) {
        http_response_code(400);
        exit('Your form expired. Please go back, reload the page and try again.');
    }
}

function current_user(): ?array {
    static $u = false;
    if ($u === false) $u = isset($_SESSION['uid']) ? user_by_id((int) $_SESSION['uid']) : null;
    return $u;
}
function login_user(array $u): void { session_regenerate_id(true); $_SESSION['uid'] = (int) $u['id']; }
function logout_user(): void { $_SESSION = []; session_regenerate_id(true); }

function require_login(): array {
    $u = current_user();
    if (!$u) redirect('login.php?next=' . urlencode(basename($_SERVER['PHP_SELF'])));
    return $u;
}
function require_admin(): array {
    $u = current_user();
    if (!$u || $u['role'] !== 'admin') { global $ROOT; header('Location: ' . $ROOT . 'login.php'); exit; }
    return $u;
}

function flash(?string $msg = null, string $kind = 'ok'): ?array {
    if ($msg !== null) { $_SESSION['flash'] = [$msg, $kind]; return null; }
    $f = $_SESSION['flash'] ?? null;
    unset($_SESSION['flash']);
    return $f;
}

/* cart lives in the session: [product_id => qty] */
function cart(): array { return $_SESSION['cart'] ?? []; }
function cart_count(): int { return array_sum(cart()); }
function cart_set(int $pid, int $qty): void {
    if ($qty <= 0) unset($_SESSION['cart'][$pid]);
    else $_SESSION['cart'][$pid] = min($qty, 10);
}
function cart_clear(): void { $_SESSION['cart'] = []; }

/** Only local paths for "next" redirects (no open redirect). */
function safe_next(?string $n): string {
    return ($n && preg_match('/^[a-z_]+\.php(\?[\w=&%.-]*)?$/i', $n)) ? $n : 'index.php';
}
