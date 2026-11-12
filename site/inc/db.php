<?php
/* The ONLY file that talks to the database. Pages call the functions below, never SQL.
 * Every query uses prepared statements. To move off MySQL, re-implement these functions. */
require_once __DIR__ . '/config.php';

function db(): PDO {
    static $pdo = null;
    if ($pdo === null) {
        $pdo = new PDO('mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4', DB_USER, DB_PASS, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]);
    }
    return $pdo;
}

function q_all(string $sql, array $p = []): array { $s = db()->prepare($sql); $s->execute($p); return $s->fetchAll(); }
function q_one(string $sql, array $p = []): ?array { $s = db()->prepare($sql); $s->execute($p); $r = $s->fetch(); return $r ?: null; }
function q_val(string $sql, array $p = []) { $s = db()->prepare($sql); $s->execute($p); return $s->fetchColumn(); }
function q_exec(string $sql, array $p = []): int { $s = db()->prepare($sql); $s->execute($p); return $s->rowCount(); }

const PRODUCT_COLS = 'id, name, articleType, baseColour, gender, `usage`, masterCategory, subCategory, price, stock, image';

/** Product columns prefixed with a table alias, for queries that join other tables. */
function pcols(string $a): string {
    return implode(', ', array_map(fn($c) => "$a.$c", explode(', ', PRODUCT_COLS)));
}

/* ---------- users ---------- */
function user_by_email(string $email): ?array { return q_one('SELECT * FROM users WHERE email = ?', [$email]); }
function user_by_id(int $id): ?array { return q_one('SELECT id, name, email, role FROM users WHERE id = ?', [$id]); }
function user_create(string $name, string $email, string $hash): int {
    q_exec('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)', [$name, $email, $hash]);
    return (int) db()->lastInsertId();
}

/* ---------- catalogue ---------- */
function product_get(int $id): ?array { return q_one('SELECT ' . PRODUCT_COLS . ' FROM products WHERE id = ?', [$id]); }

function products_by_ids(array $ids): array {
    $ids = array_values(array_filter(array_map('intval', $ids)));
    if (!$ids) return [];
    $in = implode(',', array_fill(0, count($ids), '?'));
    $rows = q_all('SELECT ' . PRODUCT_COLS . " FROM products WHERE id IN ($in)", $ids);
    $by = [];
    foreach ($rows as $r) $by[$r['id']] = $r;
    return $by;
}

/** Distinct values for the filter dropdowns. */
function facet_values(string $col): array {
    $allowed = ['articleType' => 'articleType', 'baseColour' => 'baseColour', 'gender' => 'gender', 'usage' => '`usage`'];
    if (!isset($allowed[$col])) return [];
    $c = $allowed[$col];
    return array_column(q_all("SELECT DISTINCT $c AS v FROM products WHERE $c IS NOT NULL AND $c <> '' ORDER BY v"), 'v');
}

/** Text search + filters. $f keys: q, articleType, baseColour, gender, usage, min, max, sort. */
function products_search(array $f, int $limit = 24, int $offset = 0): array {
    $where = ['1=1']; $p = [];
    if (($f['q'] ?? '') !== '') {
        foreach (preg_split('/\s+/', trim($f['q'])) as $w) {
            $where[] = '(name LIKE ? OR articleType LIKE ? OR baseColour LIKE ? OR `usage` LIKE ?)';
            array_push($p, "%$w%", "%$w%", "%$w%", "%$w%");
        }
    }
    foreach (['articleType' => 'articleType', 'baseColour' => 'baseColour', 'gender' => 'gender', 'usage' => '`usage`'] as $k => $col) {
        if (($f[$k] ?? '') !== '') { $where[] = "$col = ?"; $p[] = $f[$k]; }
    }
    if (($f['min'] ?? '') !== '') { $where[] = 'price >= ?'; $p[] = (float) $f['min']; }
    if (($f['max'] ?? '') !== '') { $where[] = 'price <= ?'; $p[] = (float) $f['max']; }
    $order = ['price_asc' => 'price ASC', 'price_desc' => 'price DESC', 'new' => 'id DESC'][$f['sort'] ?? ''] ?? 'name ASC';
    $w = implode(' AND ', $where);
    $total = (int) q_val("SELECT COUNT(*) FROM products WHERE $w", $p);
    $rows = q_all('SELECT ' . PRODUCT_COLS . " FROM products WHERE $w ORDER BY $order LIMIT " . (int) $limit . ' OFFSET ' . (int) $offset, $p);
    return ['total' => $total, 'rows' => $rows];
}

/** Rank by how many predicted tags match (photo search). Tag values must be exact class names. */
function products_matching_tags(array $t, int $limit = 24): array {
    $score = []; $p = [];
    foreach (['articleType' => ['articleType', 4], 'baseColour' => ['baseColour', 2], 'gender' => ['gender', 1], 'usage' => ['`usage`', 1]] as $k => [$col, $wt]) {
        if (!empty($t[$k])) { $score[] = "($col = ?) * $wt"; $p[] = $t[$k]; }
    }
    if (!$score) return [];
    $s = implode(' + ', $score);
    $rows = q_all('SELECT ' . PRODUCT_COLS . ", ($s) AS score FROM products HAVING score > 0 ORDER BY score DESC, stock > 0 DESC, id LIMIT " . (int) $limit, $p);
    return $rows;
}

/** Same type and gender first, then colour and usage closeness. */
function products_similar(array $prod, int $limit = 8): array {
    return q_all('SELECT ' . PRODUCT_COLS . ', ((articleType = ?) * 4 + (gender = ?) * 2 + (baseColour = ?) * 2 + (`usage` = ?)) AS score
        FROM products WHERE id <> ? AND articleType = ? ORDER BY score DESC, ABS(price - ?) LIMIT ' . (int) $limit,
        [$prod['articleType'], $prod['gender'], $prod['baseColour'], $prod['usage'], $prod['id'], $prod['articleType'], $prod['price']]);
}

/** Products that appear in the same orders as $id, most frequent first. */
function products_bought_together(int $id, int $limit = 8): array {
    return q_all('SELECT ' . pcols('p') . ', COUNT(*) AS n
        FROM order_items a JOIN order_items b ON a.order_id = b.order_id AND b.product_id <> a.product_id
        JOIN products p ON p.id = b.product_id
        WHERE a.product_id = ? GROUP BY p.id ORDER BY n DESC, p.id LIMIT ' . (int) $limit, [$id]);
}

function products_popular(int $limit = 12): array {
    return q_all('SELECT ' . pcols('p') . ', COALESCE(SUM(oi.qty), 0) AS sold
        FROM products p LEFT JOIN order_items oi ON oi.product_id = p.id
        GROUP BY p.id ORDER BY sold DESC, p.id LIMIT ' . (int) $limit);
}

function products_newest(int $limit = 12): array {
    return q_all('SELECT ' . PRODUCT_COLS . ' FROM products ORDER BY created_at DESC, id DESC LIMIT ' . (int) $limit);
}

/** Personal picks from the user's own views: their most viewed type and colour. */
function products_for_user(int $userId, int $limit = 12): array {
    $top = q_one('SELECT p.articleType, p.baseColour, COUNT(*) AS n FROM views v JOIN products p ON p.id = v.product_id
        WHERE v.user_id = ? GROUP BY p.articleType, p.baseColour ORDER BY n DESC LIMIT 1', [$userId]);
    if (!$top) return ['basis' => null, 'rows' => []];
    $rows = q_all('SELECT ' . PRODUCT_COLS . ', ((articleType = ?) * 2 + (baseColour = ?)) AS score FROM products
        WHERE (articleType = ? OR baseColour = ?) AND id NOT IN (SELECT product_id FROM views WHERE user_id = ?)
        ORDER BY score DESC, stock > 0 DESC, id DESC LIMIT ' . (int) $limit,
        [$top['articleType'], $top['baseColour'], $top['articleType'], $top['baseColour'], $userId]);
    return ['basis' => $top, 'rows' => $rows];
}

function view_record(int $userId, int $productId): void {
    q_exec('INSERT INTO views (user_id, product_id) VALUES (?, ?)', [$userId, $productId]);
}

/* ---------- admin: products ---------- */
function product_save(array $d, ?int $id = null): int {
    $vals = [$d['name'], $d['articleType'], $d['baseColour'], $d['gender'], $d['usage'], $d['masterCategory'], $d['subCategory'] ?? null, $d['price'], $d['stock'], $d['image']];
    if ($id) {
        q_exec('UPDATE products SET name=?, articleType=?, baseColour=?, gender=?, `usage`=?, masterCategory=?, subCategory=?, price=?, stock=?, image=? WHERE id=?', array_merge($vals, [$id]));
        return $id;
    }
    q_exec('INSERT INTO products (name, articleType, baseColour, gender, `usage`, masterCategory, subCategory, price, stock, image) VALUES (?,?,?,?,?,?,?,?,?,?)', $vals);
    return (int) db()->lastInsertId();
}

function products_admin_list(string $q, int $limit, int $offset): array {
    $p = $q !== '' ? ["%$q%", "%$q%"] : [];
    $w = $q !== '' ? 'WHERE name LIKE ? OR articleType LIKE ?' : '';
    return ['total' => (int) q_val("SELECT COUNT(*) FROM products $w", $p),
            'rows' => q_all('SELECT ' . PRODUCT_COLS . " FROM products $w ORDER BY id DESC LIMIT " . (int) $limit . ' OFFSET ' . (int) $offset, $p)];
}

/* ---------- orders ---------- */
/** Creates an order from [product_id => qty] inside a transaction; prices and stock come from the DB. */
function order_create(int $userId, array $cart, string $address): int {
    $pdo = db();
    $pdo->beginTransaction();
    try {
        $total = 0; $lines = [];
        foreach ($cart as $pid => $qty) {
            $p = q_one('SELECT id, price, stock FROM products WHERE id = ? FOR UPDATE', [(int) $pid]);
            if (!$p) continue;
            $qty = max(1, min((int) $qty, 10));
            if ($p['stock'] < $qty) throw new RuntimeException('Not enough stock for one of the items.');
            $lines[] = [$p['id'], $qty, $p['price']];
            $total += $qty * $p['price'];
        }
        if (!$lines) throw new RuntimeException('Your cart is empty.');
        q_exec('INSERT INTO orders (user_id, total, status, address) VALUES (?, ?, ?, ?)', [$userId, $total, 'placed', $address]);
        $oid = (int) $pdo->lastInsertId();
        foreach ($lines as [$pid, $qty, $price]) {
            q_exec('INSERT INTO order_items (order_id, product_id, qty, price) VALUES (?, ?, ?, ?)', [$oid, $pid, $qty, $price]);
            q_exec('UPDATE products SET stock = stock - ? WHERE id = ?', [$qty, $pid]);
        }
        $pdo->commit();
        return $oid;
    } catch (Throwable $e) {
        $pdo->rollBack();
        throw $e;
    }
}

function orders_for_user(int $userId): array {
    return q_all('SELECT id, total, status, created_at FROM orders WHERE user_id = ? ORDER BY created_at DESC', [$userId]);
}

function order_items(int $orderId): array {
    return q_all('SELECT oi.qty, oi.price, p.id, p.name, p.image FROM order_items oi JOIN products p ON p.id = oi.product_id WHERE oi.order_id = ?', [$orderId]);
}

function orders_admin_list(string $status, int $limit, int $offset): array {
    $w = $status !== '' ? 'WHERE o.status = ?' : '';
    $p = $status !== '' ? [$status] : [];
    return ['total' => (int) q_val("SELECT COUNT(*) FROM orders o $w", $p),
            'rows' => q_all("SELECT o.id, o.total, o.status, o.created_at, u.name, u.email,
                (SELECT SUM(qty) FROM order_items WHERE order_id = o.id) AS items
                FROM orders o JOIN users u ON u.id = o.user_id $w ORDER BY o.created_at DESC LIMIT " . (int) $limit . ' OFFSET ' . (int) $offset, $p)];
}

function order_set_status(int $id, string $status): void {
    if (in_array($status, ['placed', 'shipped', 'delivered', 'cancelled'], true)) {
        q_exec('UPDATE orders SET status = ? WHERE id = ?', [$status, $id]);
    }
}

/* ---------- dashboard metrics ---------- */
function metrics_summary(int $days): array {
    return q_one("SELECT COUNT(*) AS orders, COALESCE(SUM(total), 0) AS revenue, COALESCE(AVG(total), 0) AS aov,
        COUNT(DISTINCT user_id) AS customers FROM orders WHERE status <> 'cancelled' AND created_at >= DATE_SUB(NOW(), INTERVAL ? DAY)", [$days]);
}

function metrics_revenue_by_day(int $days): array {
    return q_all("SELECT DATE(created_at) AS d, SUM(total) AS revenue, COUNT(*) AS orders FROM orders
        WHERE status <> 'cancelled' AND created_at >= DATE_SUB(CURDATE(), INTERVAL ? DAY) GROUP BY DATE(created_at) ORDER BY d", [$days]);
}

function metrics_by_category(int $days): array {
    return q_all("SELECT p.articleType AS label, SUM(oi.qty) AS units, SUM(oi.qty * oi.price) AS revenue
        FROM order_items oi JOIN orders o ON o.id = oi.order_id JOIN products p ON p.id = oi.product_id
        WHERE o.status <> 'cancelled' AND o.created_at >= DATE_SUB(NOW(), INTERVAL ? DAY)
        GROUP BY p.articleType ORDER BY revenue DESC LIMIT 10", [$days]);
}

function metrics_top_products(int $days, int $limit = 8): array {
    return q_all("SELECT p.id, p.name, p.image, SUM(oi.qty) AS units, SUM(oi.qty * oi.price) AS revenue
        FROM order_items oi JOIN orders o ON o.id = oi.order_id JOIN products p ON p.id = oi.product_id
        WHERE o.status <> 'cancelled' AND o.created_at >= DATE_SUB(NOW(), INTERVAL ? DAY)
        GROUP BY p.id ORDER BY units DESC, revenue DESC LIMIT " . (int) $limit, [$days]);
}

function metrics_low_stock(int $limit = 8): array {
    return q_all('SELECT id, name, image, stock FROM products ORDER BY stock ASC, id LIMIT ' . (int) $limit);
}
