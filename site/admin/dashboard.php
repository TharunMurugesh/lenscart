<?php
$ROOT = '../';
require __DIR__ . '/../inc/layout.php';
require __DIR__ . '/_nav.php';
require_admin();
$days = in_array((int) ($_GET['days'] ?? 30), [7, 30, 60, 90], true) ? (int) $_GET['days'] : 30;
$sum = metrics_summary($days);
$byDay = metrics_revenue_by_day($days);
$byCat = metrics_by_category($days);
$top = metrics_top_products($days);
$low = metrics_low_stock();

// fill missing days with zero so the line is honest
$series = [];
for ($i = $days; $i >= 0; $i--) $series[date('Y-m-d', strtotime("-$i day"))] = 0;
foreach ($byDay as $r) if (isset($series[$r['d']])) $series[$r['d']] = (float) $r['revenue'];

page_header('Admin dashboard', 'admin');
admin_nav('dash');
?>
<div class="row" style="justify-content:space-between">
  <h1><?= icon('layout-dashboard') ?>Store performance</h1>
  <nav class="subnav" aria-label="Period">
    <?php foreach ([7, 30, 60, 90] as $d): ?><a href="?days=<?= $d ?>" class="<?= $d === $days ? 'on' : '' ?>">Last <?= $d ?> days</a><?php endforeach; ?>
  </nav>
</div>
<p class="sub">Orders and prices are demo data seeded for this hackathon; new orders placed on the site are added live.</p>

<div class="kpis">
  <div class="card kpi"><div class="k"><?= icon('chart-line') ?>Revenue</div><div class="v"><?= money($sum['revenue']) ?></div></div>
  <div class="card kpi"><div class="k"><?= icon('receipt') ?>Orders</div><div class="v"><?= number_format((int) $sum['orders']) ?></div></div>
  <div class="card kpi"><div class="k"><?= icon('shopping-cart') ?>Average order value</div><div class="v"><?= money($sum['aov']) ?></div></div>
  <div class="card kpi"><div class="k"><?= icon('user') ?>Customers who ordered</div><div class="v"><?= number_format((int) $sum['customers']) ?></div></div>
</div>

<div class="charts">
  <section class="card"><h2>Revenue per day</h2><div class="chart-box"><canvas id="c-rev"></canvas></div></section>
  <section class="card"><h2>Revenue by article type (top 10)</h2><div class="chart-box"><canvas id="c-cat"></canvas></div></section>
  <section class="card">
    <h2>Top products</h2>
    <ul class="mini">
      <?php foreach ($top as $p): ?>
        <li><img src="../<?= e($p['image']) ?>" alt=""><a href="../product.php?id=<?= (int) $p['id'] ?>"><?= e($p['name']) ?></a><span><?= (int) $p['units'] ?> sold</span><b><?= money($p['revenue']) ?></b></li>
      <?php endforeach; ?>
      <?php if (!$top): ?><li class="sub">No orders in this period.</li><?php endif; ?>
    </ul>
  </section>
  <section class="card">
    <h2>Lowest stock</h2>
    <ul class="mini">
      <?php foreach ($low as $p): ?>
        <li><img src="../<?= e($p['image']) ?>" alt=""><a href="product_edit.php?id=<?= (int) $p['id'] ?>"><?= e($p['name']) ?></a><span></span><b class="<?= $p['stock'] <= 0 ? 'muted' : '' ?>"><?= (int) $p['stock'] ?> left</b></li>
      <?php endforeach; ?>
    </ul>
  </section>
</div>

<script src="../vendor/chart.umd.min.js"></script>
<script>
(function () {
  const css = getComputedStyle(document.documentElement);
  const accent = css.getPropertyValue("--accent").trim(), line = css.getPropertyValue("--line").trim(), muted = css.getPropertyValue("--muted").trim();
  Chart.defaults.color = muted; Chart.defaults.borderColor = line; Chart.defaults.font.family = "system-ui, sans-serif";
  const inr = (v) => "₹" + Number(v).toLocaleString("en-IN", { maximumFractionDigits: 0 });
  new Chart(document.getElementById("c-rev"), {
    type: "line",
    data: { labels: <?= json_encode(array_map(fn($d) => date('j M', strtotime($d)), array_keys($series))) ?>,
            datasets: [{ data: <?= json_encode(array_values($series)) ?>, borderColor: accent, backgroundColor: accent, borderWidth: 2, pointRadius: 0, tension: 0.25 }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => inr(c.parsed.y) } } },
               scales: { y: { beginAtZero: true, ticks: { callback: inr } }, x: { ticks: { maxTicksLimit: 8 } } } },
  });
  new Chart(document.getElementById("c-cat"), {
    type: "bar",
    data: { labels: <?= json_encode(array_column($byCat, 'label')) ?>,
            datasets: [{ data: <?= json_encode(array_map('floatval', array_column($byCat, 'revenue'))) ?>, backgroundColor: accent, borderRadius: 4 }] },
    options: { indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => inr(c.parsed.x) } } },
               scales: { x: { beginAtZero: true, ticks: { callback: inr, maxTicksLimit: 5 } } } },
  });
})();
</script>
<?php page_footer();
