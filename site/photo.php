<?php
require __DIR__ . '/inc/layout.php';
page_header('Search by photo', 'photo');
?>
<h1><?= icon('camera') ?>Search by photo</h1>
<p class="sub">Our trained model reads the photo in your browser. The image is never uploaded to our server.</p>

<div class="ai">
  <div class="card">
    <label id="drop" class="drop">
      <input id="file" type="file" accept="image/*" hidden>
      <?= icon('image-up') ?>
      <b>Drop a clothing photo, or click to choose</b>
      <span>One garment per photo works best.</span>
    </label>
    <img id="preview" class="preview" alt="Your photo" hidden>
  </div>

  <div class="card" id="result" hidden>
    <div id="stub-note" class="notice" hidden><?= icon('info') ?><span><b>Demo data.</b> The model file is not loaded, so these tags are fixed examples, not predictions.</span></div>
    <h2><?= icon('scan-search') ?>What the model sees <span class="sub" id="ms"></span></h2>
    <div id="preds" class="preds"></div>
  </div>

  <div class="card" id="heat-card" hidden>
    <h2><?= icon('flame') ?>Where it looked</h2>
    <p class="sub">Brighter = more evidence for that answer. % = share of the evidence on the garment.</p>
    <div id="heat" class="heat"></div>
  </div>
</div>

<div id="busy" class="empty" hidden><?= icon('loader-circle', 'spin') ?> Reading the photo…</div>
<div id="err" class="flash bad" hidden></div>

<section class="block" id="matches-block" hidden>
  <h2><?= icon('shirt') ?><span id="matches-title">Matching items in our store</span></h2>
  <p class="sub" id="match-basis"></p>
  <div id="match-hint" class="notice" hidden><?= icon('info') ?><span>The model is not sure what this item is (<b id="match-hint-p"></b> for its best guess), so these matches may be off. It learned from product photos: try the item on its own, seen from the side or front, on a plain background.</span></div>
  <div id="matches" class="grid"></div>
</section>

<script src="ai/vendor/ort.min.js"></script>
<script src="ai/lensai.js"></script>
<script src="js/ai-stub.js"></script>
<script src="js/photo.js"></script>
<?php page_footer();
