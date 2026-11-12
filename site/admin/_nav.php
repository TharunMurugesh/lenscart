<?php
function admin_nav(string $on): void {
    echo '<nav class="subnav">';
    foreach ([['dashboard.php', 'Dashboard', 'chart-line', 'dash'], ['products.php', 'Products', 'package', 'products'],
              ['product_edit.php', 'Add product', 'plus', 'add'], ['orders.php', 'Orders', 'receipt', 'orders']] as [$h, $l, $i, $k]) {
        echo '<a href="' . $h . '" class="' . ($on === $k ? 'on' : '') . '">' . icon($i) . e($l) . '</a>';
    }
    echo '</nav>';
}
