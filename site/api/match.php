<?php
/* GET api/match.php?articleType=&baseColour=&gender=&usage=  ->  {typeInStore, items}: products ranked by
 * how many predicted tags they share (type weighs most). typeInStore is false when the shop does not sell
 * the predicted type (e.g. innerwear); items then match on colour, gender and occasion only.
 * Only class names from labels.php are accepted. */
$ROOT = '../';
require __DIR__ . '/../inc/auth.php';
require __DIR__ . '/../inc/labels.php';
header('Content-Type: application/json; charset=utf-8');

$tags = [];
foreach (LABELS as $head => $names) {
    $v = (string) ($_GET[$head] ?? '');
    if ($v !== '' && in_array($v, $names, true)) $tags[$head] = $v;
}
$typeInStore = isset($tags['articleType']) && products_count_of_type($tags['articleType']) > 0;
$rows = products_matching_tags($tags, 24);
echo json_encode(['typeInStore' => $typeInStore, 'items' => array_map(fn($p) => [
    'id' => (int) $p['id'], 'name' => $p['name'], 'price' => money($p['price']), 'image' => $p['image'],
    'articleType' => $p['articleType'], 'baseColour' => $p['baseColour'], 'gender' => $p['gender'],
    'usage' => $p['usage'], 'inStock' => $p['stock'] > 0,
], $rows)]);
