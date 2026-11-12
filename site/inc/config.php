<?php
// Never show errors to visitors (no file paths or stack traces); log them instead.
ini_set('display_errors', '0');
ini_set('log_errors', '1');
error_reporting(E_ALL);

/** Short, friendly error page. Details go to the PHP error log only. */
function fail_page(string $msg, int $code = 500): void {
    if (!headers_sent()) { http_response_code($code); header('Content-Type: text/html; charset=utf-8'); }
    echo '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        . '<title>LensCart</title><body style="font:16px system-ui,sans-serif;background:#f5f6f4;color:#1f2a2e;'
        . 'display:grid;place-items:center;min-height:90vh;margin:0;padding:16px"><div style="max-width:420px;'
        . 'background:#fff;border:1px solid #e2e6e4;border-radius:8px;padding:24px"><h1 style="font-size:20px;margin:0 0 8px">LensCart</h1><p style="margin:0">'
        . htmlspecialchars($msg, ENT_QUOTES, 'UTF-8') . '</p></div></body>';
    exit;
}
set_exception_handler(function (Throwable $e) {
    error_log('LensCart: ' . $e);
    fail_page('Something went wrong on our side. Please try again in a moment.');
});

// Database settings. XAMPP defaults below; change these four lines on the web host.
const DB_HOST = '127.0.0.1';
const DB_NAME = 'lenscart';
const DB_USER = 'root';
const DB_PASS = '';

const SITE_NAME = 'LensCart';
const CURRENCY = '₹';
