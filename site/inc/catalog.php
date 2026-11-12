<?php
/* Store departments (category navigation) and their queries.
 * A department is a fixed filter over the products table. Used by category.php,
 * and by the header category bar / home tiles in layout.php and index.php. */
require_once __DIR__ . '/db.php';

function departments(): array {
    return [
        'men'         => ['title' => 'Men',         'icon' => 'shirt',       'blurb' => 'Shirts, T-shirts, jeans and more',     'where' => "gender = 'Men' AND masterCategory = 'Apparel'", 'params' => ['gender' => 'Men']],
        'women'       => ['title' => 'Women',       'icon' => 'shirt',       'blurb' => 'Kurtas, tops, dresses and more',        'where' => "gender = 'Women' AND masterCategory = 'Apparel'", 'params' => ['gender' => 'Women']],
        'kids'        => ['title' => 'Kids',        'icon' => 'sparkles',    'blurb' => 'For boys and girls',                    'where' => "gender IN ('Boys', 'Girls')", 'params' => []],
        'footwear'    => ['title' => 'Footwear',    'icon' => 'package',     'blurb' => 'Shoes, sandals, heels, flip flops',     'where' => "masterCategory = 'Footwear'", 'params' => []],
        'ethnic'      => ['title' => 'Ethnic wear', 'icon' => 'sparkles',    'blurb' => 'Kurtas, kurtis, sarees and more',       'where' => "`usage` = 'Ethnic'", 'params' => ['usage' => 'Ethnic']],
        'sports'      => ['title' => 'Sportswear',  'icon' => 'activity',    'blurb' => 'Track wear, sports shoes, gear',        'where' => "`usage` = 'Sports'", 'params' => ['usage' => 'Sports']],
        'watches'     => ['title' => 'Watches',     'icon' => 'timer',       'blurb' => 'Analog and digital',                    'where' => "articleType = 'Watches'", 'params' => []],
        'accessories' => ['title' => 'Accessories', 'icon' => 'tag',         'blurb' => 'Bags, wallets, belts, sunglasses',      'where' => "masterCategory = 'Accessories' AND articleType <> 'Watches'", 'params' => []],
    ];
}

function department(string $slug): ?array {
    $d = departments();
    return isset($d[$slug]) ? $d[$slug] + ['slug' => $slug] : null;
}

/** Article types inside a department, with a count and one cover photo each. */
function dept_types(array $d): array {
    return q_all("SELECT articleType, COUNT(*) AS n, MIN(image) AS image
                    FROM products WHERE {$d['where']}
                   GROUP BY articleType ORDER BY n DESC");
}

/** Colours available in a department (for quick filter chips). */
function dept_colours(array $d, int $limit = 10): array {
    return q_all("SELECT baseColour, COUNT(*) AS n FROM products
                   WHERE {$d['where']} AND baseColour IS NOT NULL
                   GROUP BY baseColour ORDER BY n DESC LIMIT " . (int) $limit);
}

/** Best sellers by units ordered; falls back to newest when a department has no orders. */
function dept_best_sellers(array $d, int $limit = 12): array {
    $rows = q_all('SELECT ' . pcols('p') . ", SUM(oi.qty) AS sold
                     FROM products p JOIN order_items oi ON oi.product_id = p.id
                    WHERE " . str_replace(['gender', 'masterCategory', '`usage`', 'articleType'],
                                          ['p.gender', 'p.masterCategory', 'p.`usage`', 'p.articleType'], $d['where']) . "
                    GROUP BY p.id ORDER BY sold DESC LIMIT " . (int) $limit);
    return $rows ?: dept_products($d, 'new', $limit);
}

function dept_products(array $d, string $sort = 'new', int $limit = 12, ?float $maxPrice = null): array {
    $order = ['new' => 'id DESC', 'price_asc' => 'price ASC', 'price_desc' => 'price DESC'][$sort] ?? 'id DESC';
    $where = $d['where'];
    $p = [];
    if ($maxPrice !== null) { $where .= ' AND price <= ?'; $p[] = $maxPrice; }
    return q_all('SELECT ' . PRODUCT_COLS . " FROM products WHERE $where AND stock > 0
                  ORDER BY $order LIMIT " . (int) $limit, $p);
}

function dept_count(array $d): int {
    return (int) q_val("SELECT COUNT(*) FROM products WHERE {$d['where']}");
}

/** Cover photo per department (most stocked article type's first image), for home tiles. */
function dept_covers(): array {
    $out = [];
    foreach (departments() as $slug => $d) {
        // several candidates per department, so no two tiles show the same photo
        $cands = q_all("SELECT image FROM products WHERE {$d['where']} ORDER BY stock DESC, id LIMIT 10");
        $out[$slug] = null;
        foreach ($cands as $c) {
            if (!in_array($c['image'], $out, true)) { $out[$slug] = $c['image']; break; }
        }
    }
    return $out;
}
