<?php
/* GET api/match.php?articleType=&baseColour=&gender=&usage=  ->  JSON list of products ranked by
 * how many predicted tags they share (type weighs most). Only class names from labels.php are accepted. */
$ROOT = '../';
require __DIR__ . '/../inc/auth.php';
require __DIR__ . '/../inc/labels.php';
header('Content-Type: application/json; charset=utf-8');

$tags = [];
foreach (LABELS as $head => $names) {
    $v = (string) ($_GET[$head] ?? '');
    if ($v !== '' && in_array($v, $names, true)) $tags[$head] = $v;
}
$rows = products_matching_tags($tags, 24);
echo json_encode(array_map(fn($p) => [
    'id' => (int) $p['id'], 'name' => $p['name'], 'price' => money($p['price']), 'image' => $p['image'],
    'articleType' => $p['articleType'], 'baseColour' => $p['baseColour'], 'gender' => $p['gender'],
    'usage' => $p['usage'], 'inStock' => $p['stock'] > 0,
], $rows));
