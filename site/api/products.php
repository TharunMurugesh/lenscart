<?php
/* GET api/products.php?ids=12,7,99  ->  JSON product cards in the SAME order as the ids.
 * Used by photo search after the in-browser model ranks the catalogue by visual similarity.
 * Only positive integers are accepted, at most 48; unknown ids are skipped. */
$ROOT = '../';
require __DIR__ . '/../inc/auth.php';
header('Content-Type: application/json; charset=utf-8');

$ids = [];
foreach (explode(',', (string) ($_GET['ids'] ?? '')) as $part) {
    if (ctype_digit($part) && (int) $part > 0) $ids[] = (int) $part;
    if (count($ids) >= 48) break;
}
$ids = array_values(array_unique($ids));
$found = products_by_ids($ids);
$out = [];
foreach ($ids as $id) {
    if (!isset($found[$id])) continue;
    $p = $found[$id];
    $out[] = ['id' => (int) $p['id'], 'name' => $p['name'], 'price' => money($p['price']), 'image' => $p['image'],
              'articleType' => $p['articleType'], 'baseColour' => $p['baseColour'], 'gender' => $p['gender'],
              'usage' => $p['usage'], 'inStock' => $p['stock'] > 0];
}
echo json_encode($out);
