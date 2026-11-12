<?php
/* "Our AI model": how the vision model was built and how well it works.
 * Every number comes from data/model_report.json, generated from the training run's
 * results by scripts/build_model_report.py. Nothing here is typed by hand. */
require_once __DIR__ . '/inc/layout.php';

$R = json_decode(file_get_contents(__DIR__ . '/data/model_report.json'), true);
$HEADS = ['articleType' => 'Article type', 'baseColour' => 'Colour', 'gender' => 'Gender', 'usage' => 'Usage'];

function pct($v, int $d = 1): string { return $v === null ? '–' : number_format($v * 100, $d) . '%'; }
function num($v, int $d = 3): string { return $v === null ? '–' : number_format((float) $v, $d); }
function ci(array $R, string $head, string $metric): ?array {
    foreach ($R['test_ci'] as $r) if ($r['head'] === $head && $r['metric'] === $metric) return $r;
    return null;
}
$tm = [];
foreach ($R['test_metrics'] as $r) $tm[$r['head']] = $r;
$fc = $R['final_counts'];

page_header('Our AI model', 'model');
?>
<link rel="stylesheet" href="<?= url('css/model.css') ?>">

<section class="m-hero">
  <div>
    <p class="m-kicker"><?= icon('brain-circuit') ?> Computer vision model</p>
    <h1>One photo in, four answers out.</h1>
    <p class="m-lead">An EfficientNet-B0 network we fine-tuned on <?= number_format($fc['train']) ?> fashion product photos.
      It reads an image and predicts the article type, colour, gender and usage, then shows where in the image it looked.
      Every score below comes from <?= number_format($fc['test']) ?> test photos the model never saw during training.</p>
  </div>
  <div class="m-tiles">
    <?php foreach ($HEADS as $h => $name): $c = ci($R, $h, 'accuracy'); ?>
      <div class="m-tile">
        <div class="m-tile-k"><?= e($name) ?></div>
        <div class="m-tile-v"><?= pct($tm[$h]['accuracy']) ?></div>
        <div class="m-tile-s">accuracy · 95% CI <?= pct($c['ci95_low']) ?>–<?= pct($c['ci95_high']) ?></div>
        <div class="m-tile-s">macro F1 <?= num($tm[$h]['macro_f1']) ?> · <?= (int) $R['classes'][$h] ?> classes</div>
      </div>
    <?php endforeach; ?>
  </div>
</section>

<nav class="m-sub" aria-label="Sections">
  <a href="#try"><?= icon('image-up') ?>Try it</a>
  <a href="#test"><?= icon('target') ?>Test mode</a>
  <a href="#data"><?= icon('database') ?>Data</a>
  <a href="#training"><?= icon('activity') ?>Training</a>
  <a href="#results"><?= icon('chart-line') ?>Results</a>
  <a href="#compare"><?= icon('layers') ?>Comparisons</a>
</nav>

<section id="try" class="m-sec">
  <h2><?= icon('image-up') ?>Try it on any clothing photo</h2>
  <p class="m-note">Runs entirely in your browser. The image is not uploaded anywhere.
    Heat maps are class activation maps: the brighter the area, the more it pushed the model towards its answer.
    "Focus" is the share of that heat that falls on the garment rather than the background.</p>
  <label class="m-drop" id="tryDrop">
    <input type="file" id="tryFile" accept="image/*" hidden>
    <?= icon('upload') ?><span>Choose or drop an image</span>
  </label>
  <div id="tryStatus" class="m-status"></div>
  <div id="tryOut" class="m-heads"></div>
</section>

<section id="test" class="m-sec">
  <h2><?= icon('target') ?>Test mode: check the model yourself</h2>
  <p class="m-note">A random photo from the held-out test set, with the label from the dataset and the model's answer.
    Green means it matched the dataset label, red means it didn't. Press "Run live" to run the model in your browser on the same photo.</p>
  <div class="m-test">
    <div class="m-test-img"><img id="testImg" alt="Test image"></div>
    <div class="m-test-body">
      <table class="m-table" id="testTable">
        <thead><tr><th>Question</th><th>Dataset label</th><th>Model (recorded)</th><th>Model (live)</th></tr></thead>
        <tbody></tbody>
      </table>
      <div class="m-actions">
        <button class="m-btn" id="testNext"><?= icon('shuffle') ?>Next random image</button>
        <button class="m-btn ghost" id="testLive"><?= icon('play') ?>Run live</button>
        <span class="m-score" id="testScore"></span>
      </div>
    </div>
  </div>
</section>

<section id="data" class="m-sec">
  <h2><?= icon('database') ?>The data</h2>
  <div class="m-cols">
    <div>
      <p class="m-note">Fashion Product Images dataset (Kaggle): Indian e-commerce product photos with labels.
        We kept apparel, footwear and accessories, and article types with at least 100 images.
        The split is stratified by article type and grouped by product name, so the same product never sits in both training and test.
        Near-duplicate photos (perceptual hash distance ≤ <?= (int) $R['dedup']['max_hamming'] ?>) were removed from validation and test.</p>
      <table class="m-table">
        <thead><tr><th>Step</th><th class="r">Images</th></tr></thead>
        <tbody>
          <?php foreach ($R['data_steps'] as $s): if (in_array(trim($s['step']), ['train', 'val', 'test'], true)) continue; ?>
            <tr><td><?= e($s['step']) ?></td><td class="r"><?= number_format($s['images']) ?></td></tr>
          <?php endforeach; ?>
          <tr><td>Near-duplicates removed from val/test</td><td class="r">−<?= number_format($R['dedup']['dropped']) ?></td></tr>
          <tr class="m-strong"><td>Train / validation / test</td><td class="r"><?= number_format($fc['train']) ?> / <?= number_format($fc['val']) ?> / <?= number_format($fc['test']) ?></td></tr>
        </tbody>
      </table>
    </div>
    <figure class="m-fig"><img src="<?= url('img/model/fig1_article_types.png') ?>" alt="Images per article type" loading="lazy">
      <figcaption>Images per article type (log scale): a long tail, which is why we report macro F1.</figcaption></figure>
  </div>
</section>

<section id="training" class="m-sec">
  <h2><?= icon('activity') ?>Training</h2>
  <div class="m-cols">
    <ul class="m-facts">
      <li><b>Backbone</b> EfficientNet-B0 pre-trained on ImageNet (transfer learning)</li>
      <li><b>Heads</b> one linear layer per question, sharing the same backbone</li>
      <li><b>Schedule</b> 3 epochs with the backbone frozen, then fine-tuning, <?= (int) $R['training']['epochs'] ?> epochs in total</li>
      <li><b>Loss</b> class-weighted cross-entropy per head; unknown labels are skipped</li>
      <li><b>Augmentation</b> crops, flips, small rotations, mild brightness/contrast (no hue changes, which would corrupt colour labels)</li>
      <li><b>Best validation score</b> <?= num($R['training']['best_val_score']) ?> (mean macro F1 over the four heads)</li>
      <li><b>Training time</b> <?= number_format($R['training']['seconds'] / 60, 1) ?> minutes on one laptop GPU</li>
    </ul>
    <figure class="m-fig"><img src="<?= url('img/model/curves.png') ?>" alt="Training curves" loading="lazy">
      <figcaption>Loss and validation macro F1 per epoch.</figcaption></figure>
  </div>
</section>

<section id="results" class="m-sec">
  <h2><?= icon('chart-line') ?>Results on the test set</h2>
  <div class="m-scroll">
    <table class="m-table">
      <thead><tr><th>Question</th><th class="r">Images</th><th class="r">Accuracy</th><th class="r">Macro precision</th><th class="r">Macro recall</th><th class="r">Macro F1</th><th class="r">Top-3 accuracy</th></tr></thead>
      <tbody>
      <?php foreach ($HEADS as $h => $name): $r = $tm[$h]; ?>
        <tr><td><?= e($name) ?></td><td class="r"><?= number_format($r['n']) ?></td><td class="r"><?= pct($r['accuracy']) ?></td>
          <td class="r"><?= num($r['macro_precision']) ?></td><td class="r"><?= num($r['macro_recall']) ?></td>
          <td class="r"><b><?= num($r['macro_f1']) ?></b></td><td class="r"><?= $r['top3_accuracy'] === null ? '–' : pct($r['top3_accuracy']) ?></td></tr>
      <?php endforeach; ?>
      </tbody>
    </table>
  </div>

  <h3>Confusion matrices</h3>
  <div class="m-seg" role="tablist">
    <?php $first = true; foreach ($HEADS as $h => $name): ?>
      <button role="tab" class="<?= $first ? 'on' : '' ?>" data-cm="<?= e($h) ?>"><?= e($name) ?></button>
    <?php $first = false; endforeach; ?>
  </div>
  <figure class="m-fig wide"><img id="cmImg" src="<?= url('img/model/cm_articleType.png') ?>" alt="Confusion matrix" loading="lazy">
    <figcaption>Rows are the true class, columns the prediction, normalised per row. The diagonal is correct.</figcaption></figure>

  <div class="m-cols">
    <div>
      <h3>Most common mistakes (article type)</h3>
      <table class="m-table">
        <thead><tr><th>True</th><th>Predicted as</th><th class="r">Times</th></tr></thead>
        <tbody><?php foreach ($R['top_confusions'] as $c): ?>
          <tr><td><?= e($c['true']) ?></td><td><?= e($c['predicted']) ?></td><td class="r"><?= (int) $c['count'] ?></td></tr>
        <?php endforeach; ?></tbody>
      </table>
    </div>
    <div>
      <h3>Article-type accuracy by group</h3>
      <table class="m-table">
        <thead><tr><th>Group</th><th class="r">Images</th><th class="r">Accuracy</th><th class="r">Macro F1</th></tr></thead>
        <tbody><?php foreach ($R['audit'] as $a): ?>
          <tr><td><?= e($a['group']) ?></td><td class="r"><?= number_format($a['n']) ?></td>
            <td class="r"><?= is_numeric($a['accuracy']) ? pct($a['accuracy']) : 'N/A' ?></td>
            <td class="r"><?= is_numeric($a['macro_f1']) ? num($a['macro_f1']) : 'N/A' ?></td></tr>
        <?php endforeach; ?></tbody>
      </table>
    </div>
  </div>
</section>

<section id="compare" class="m-sec">
  <h2><?= icon('layers') ?>Comparisons we ran</h2>
  <p class="m-note">Short 6-epoch runs scored on the validation set (never the test set), to justify each design choice.</p>
  <h3>What each training choice adds</h3>
  <div class="m-scroll"><table class="m-table">
    <thead><tr><th>Run</th><th>Change</th><th class="r">Type</th><th class="r">Colour</th><th class="r">Gender</th><th class="r">Usage</th><th class="r">Mean F1</th></tr></thead>
    <tbody><?php foreach ($R['ablation'] as $a): if ($a['status'] !== 'done') continue; ?>
      <tr><td><?= e($a['run']) ?></td><td><?= e($a['change']) ?></td>
        <td class="r"><?= num($a['val_macro_f1_articleType']) ?></td><td class="r"><?= num($a['val_macro_f1_baseColour']) ?></td>
        <td class="r"><?= num($a['val_macro_f1_gender']) ?></td><td class="r"><?= num($a['val_macro_f1_usage']) ?></td>
        <td class="r"><b><?= num($a['val_macro_f1_mean']) ?></b></td></tr>
    <?php endforeach; ?></tbody>
  </table></div>

  <h3>Other backbones and baselines we tried</h3>
  <div class="m-scroll"><table class="m-table">
    <thead><tr><th>Run</th><th>Model</th><th class="r">Type</th><th class="r">Colour</th><th class="r">Gender</th><th class="r">Usage</th><th class="r">Mean F1</th></tr></thead>
    <tbody><?php foreach ($R['backbones'] as $b): ?>
      <tr><td><?= e($b['run']) ?></td><td><?= e($b['model']) ?></td>
        <td class="r"><?= num($b['val_macro_f1_articleType']) ?></td><td class="r"><?= num($b['val_macro_f1_baseColour']) ?></td>
        <td class="r"><?= num($b['val_macro_f1_gender']) ?></td><td class="r"><?= num($b['val_macro_f1_usage']) ?></td>
        <td class="r"><b><?= num($b['val_macro_f1_mean']) ?></b></td></tr>
    <?php endforeach; ?></tbody>
  </table></div>

  <div class="m-cols">
    <div>
      <h3>Finding similar products</h3>
      <table class="m-table">
        <thead><tr><th>Top results</th><th class="r">Same type</th><th class="r">Same type and colour</th></tr></thead>
        <tbody><?php $rt = $R['retrieval'][0]; foreach ([1, 5, 10] as $k): ?>
          <tr><td>Top <?= $k ?></td><td class="r"><?= pct($rt["p@{$k}_type"]) ?></td><td class="r"><?= pct($rt["p@{$k}_type_colour"]) ?></td></tr>
        <?php endforeach; ?></tbody>
      </table>
      <p class="m-note"><?= number_format($rt['queries']) ?> test photos searched against <?= number_format($rt['gallery']) ?> training photos, using the model's embeddings.</p>
    </div>
    <div>
      <h3>Speed on a laptop CPU</h3>
      <table class="m-table">
        <thead><tr><th>Backbone</th><th class="r">ms per image</th><th class="r">Parameters</th></tr></thead>
        <tbody><?php foreach ($R['latency'] as $l): ?>
          <tr><td><?= e($l['backbone']) ?></td><td class="r"><?= num($l['ms_per_image'], 1) ?></td><td class="r"><?= num($l['params_millions'], 1) ?> M</td></tr>
        <?php endforeach; ?></tbody>
      </table>
    </div>
  </div>
</section>

<script>window.MODEL_REPORT = <?= json_encode(['test' => $R['test_sample'], 'heads' => $HEADS], JSON_UNESCAPED_SLASHES) ?>;
window.SITE_ROOT = <?= json_encode(url('')) ?>;</script>
<script src="<?= url('ai/vendor/ort.min.js') ?>"></script>
<script src="<?= url('ai/lensai.js') ?>"></script>
<script src="<?= url('js/model.js') ?>"></script>
<?php page_footer(); ?>
