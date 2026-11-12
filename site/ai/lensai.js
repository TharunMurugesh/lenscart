/* LensAI: runs the LensCart vision model in the browser (onnxruntime-web, no server).
 *
 * Usage (after including ai/vendor/ort.min.js and ai/lensai.js):
 *   const r = await LensAI.analyze(imgElement);
 *   r.articleType -> [{label, p}] top 3 (same for baseColour, gender, usage)
 *   r.heatmaps[head] -> canvas (224x224) heat map of the top class over the image
 *   r.focus[head] -> share of heat inside the garment (0..1)
 *   r.embedding -> Float32Array(1280), r.ms -> inference time
 *
 * Heat maps are class activation maps (CAM): for this model (backbone -> average pool ->
 * linear head) they show exactly how much each image region adds to the predicted class.
 */
(function () {
  const here = (document.currentScript && document.currentScript.src) || "";
  const BASE = here.slice(0, here.lastIndexOf("/") + 1); // .../ai/
  const SIZE = 224;
  let session = null, meta = null, loading = null;

  async function load() {
    if (session) return;
    if (loading) return loading;
    loading = (async () => {
      ort.env.wasm.wasmPaths = BASE + "vendor/";
      ort.env.wasm.numThreads = 1; // threads need special server headers; single thread works everywhere
      meta = await (await fetch(BASE + "lensnet_meta.json")).json();
      session = await ort.InferenceSession.create(BASE + "lensnet.onnx", { executionProviders: ["wasm"] });
    })();
    return loading;
  }

  // Pad to a white square (as in training), resize to 224, return canvas + pixel data.
  function prepare(img) {
    const w = img.naturalWidth || img.width, h = img.naturalHeight || img.height;
    const side = Math.max(w, h);
    const c = document.createElement("canvas");
    c.width = c.height = SIZE;
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, SIZE, SIZE);
    const s = SIZE / side;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(img, (SIZE - w * s) / 2, (SIZE - h * s) / 2, w * s, h * s);
    return { canvas: c, data: ctx.getImageData(0, 0, SIZE, SIZE).data };
  }

  function toTensor(data) {
    const n = SIZE * SIZE, arr = new Float32Array(3 * n);
    for (let i = 0; i < n; i++) {
      for (let ch = 0; ch < 3; ch++) {
        arr[ch * n + i] = (data[i * 4 + ch] / 255 - meta.mean[ch]) / meta.std[ch];
      }
    }
    return new ort.Tensor("float32", arr, [1, 3, SIZE, SIZE]);
  }

  function softmax(v) {
    const m = Math.max(...v), e = v.map((x) => Math.exp(x - m)), s = e.reduce((a, b) => a + b, 0);
    return e.map((x) => x / s);
  }

  // Bilinear upsample a g x g grid to SIZE x SIZE (align corners off, like image resize).
  function upsample(grid, g) {
    const out = new Float32Array(SIZE * SIZE);
    for (let y = 0; y < SIZE; y++) {
      const fy = Math.min(Math.max((y + 0.5) * g / SIZE - 0.5, 0), g - 1);
      const y0 = Math.floor(fy), y1 = Math.min(y0 + 1, g - 1), dy = fy - y0;
      for (let x = 0; x < SIZE; x++) {
        const fx = Math.min(Math.max((x + 0.5) * g / SIZE - 0.5, 0), g - 1);
        const x0 = Math.floor(fx), x1 = Math.min(x0 + 1, g - 1), dx = fx - x0;
        out[y * SIZE + x] =
          grid[y0 * g + x0] * (1 - dx) * (1 - dy) + grid[y0 * g + x1] * dx * (1 - dy) +
          grid[y1 * g + x0] * (1 - dx) * dy + grid[y1 * g + x1] * dx * dy;
      }
    }
    return out;
  }

  // Garment mask: not near-white (catalogue photos have white backgrounds).
  function garmentMask(data) {
    const m = new Uint8Array(SIZE * SIZE);
    for (let i = 0; i < m.length; i++) {
      m[i] = data[i * 4] > 240 && data[i * 4 + 1] > 240 && data[i * 4 + 2] > 240 ? 0 : 1;
    }
    return m;
  }

  // Calm colour ramp: transparent -> amber -> deep orange (red is reserved for "wrong" in the UI).
  function ramp(t) {
    return [255, Math.round(220 - 140 * t), Math.round(120 - 110 * t), Math.round(200 * t)];
  }

  function heatCanvas(base, heat) {
    const c = document.createElement("canvas");
    c.width = c.height = SIZE;
    const ctx = c.getContext("2d");
    ctx.drawImage(base, 0, 0);
    const over = ctx.getImageData(0, 0, SIZE, SIZE), d = over.data;
    for (let i = 0; i < heat.length; i++) {
      const [r, g, b, a] = ramp(heat[i]), al = a / 255;
      d[i * 4] = d[i * 4] * (1 - al) + r * al;
      d[i * 4 + 1] = d[i * 4 + 1] * (1 - al) + g * al;
      d[i * 4 + 2] = d[i * 4 + 2] * (1 - al) + b * al;
    }
    ctx.putImageData(over, 0, 0);
    return c;
  }

  async function analyze(img) {
    await load();
    const t0 = performance.now();
    const { canvas, data } = prepare(img);
    const out = await session.run({ image: toTensor(data) });
    const ms = performance.now() - t0;
    const mask = garmentMask(data);
    const res = { heatmaps: {}, focus: {}, ms, embedding: out.embedding.data, input: canvas };
    for (const h of meta.heads) {
      const probs = softmax(Array.from(out["logits_" + h].data));
      const order = probs.map((p, i) => [p, i]).sort((a, b) => b[0] - a[0]);
      res[h] = order.slice(0, 3).map(([p, i]) => ({ label: meta.labels[h][i], p }));
      const top = order[0][1], cam = out["cam_" + h], g = cam.dims[2];
      const grid = cam.data.slice(top * g * g, (top + 1) * g * g);
      const up = upsample(grid, g);
      let max = 0;
      for (let i = 0; i < up.length; i++) { up[i] = Math.max(up[i], 0); if (up[i] > max) max = up[i]; }
      let inside = 0, total = 0;
      for (let i = 0; i < up.length; i++) {
        up[i] = max > 0 ? up[i] / max : 0;
        total += up[i];
        if (mask[i]) inside += up[i];
      }
      res.focus[h] = total > 0 ? inside / total : 0;
      res.heatmaps[h] = heatCanvas(canvas, up);
    }
    return res;
  }

  // ---------------------------------------------------------------- visual similarity
  // catalog_emb.bin: float16 rows (one per product, L2-normalised), order = catalog_ids.json
  let catalog = null, catalogLoading = null;

  function halfToFloat(h) {
    const s = h & 0x8000 ? -1 : 1, e = (h >> 10) & 0x1f, f = h & 0x3ff;
    if (e === 0) return s * Math.pow(2, -14) * (f / 1024);
    if (e === 31) return f ? NaN : s * Infinity;
    return s * Math.pow(2, e - 15) * (1 + f / 1024);
  }

  async function loadCatalog() {
    if (catalog) return catalog;
    if (catalogLoading) return catalogLoading;
    catalogLoading = (async () => {
      const info = await (await fetch(BASE + "catalog_ids.json")).json();
      const half = new Uint16Array(await (await fetch(BASE + "catalog_emb.bin")).arrayBuffer());
      const data = new Float32Array(half.length);
      for (let i = 0; i < half.length; i++) data[i] = halfToFloat(half[i]);
      catalog = { ids: info.ids, dim: info.dim, data };
      return catalog;
    })();
    return catalogLoading;
  }

  /** Products that LOOK most like the analysed photo: cosine similarity of the model's embeddings.
   *  Returns [{id, score}] best first; score is in -1..1 (1 = identical look). */
  async function similar(embedding, k = 24) {
    const c = await loadCatalog(), d = c.dim;
    let n = 0;
    for (let j = 0; j < d; j++) n += embedding[j] * embedding[j];
    n = Math.sqrt(n) || 1;
    const scores = new Array(c.ids.length);
    for (let i = 0; i < c.ids.length; i++) {
      let s = 0, off = i * d;
      for (let j = 0; j < d; j++) s += c.data[off + j] * embedding[j];
      scores[i] = { id: c.ids[i], score: s / n };
    }
    return scores.sort((a, b) => b.score - a.score).slice(0, k);
  }

  window.LensAI = { load, analyze, similar, loadCatalog, labels: () => meta && meta.labels };
})();
