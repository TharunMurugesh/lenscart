(function () {
  const $ = (s) => document.querySelector(s);
  const NAMES = { articleType: "Type", baseColour: "Colour", gender: "For", usage: "Occasion" };
  const pct = (v) => Math.round(v * 100) + "%";
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /** Real model first; the fixed demo stub only if the model cannot load. */
  async function runModel(img) {
    try {
      if (!window.LensAI) throw new Error("model script missing");
      return await LensAI.analyze(img);
    } catch (e) {
      console.warn("LensAI unavailable, using demo stub:", e);
      return await LensAIStub.analyze(img);
    }
  }

  async function handle(file) {
    if (!file || !file.type.startsWith("image/")) { showErr("Please choose an image file."); return; }
    $("#err").hidden = true;
    $("#busy").hidden = false;
    const img = $("#preview");
    img.src = URL.createObjectURL(file);
    img.hidden = false;
    try {
      await img.decode();
      const r = await runModel(img);
      render(r);
      await loadMatches(r);
    } catch (e) {
      showErr("Could not read this photo: " + e.message);
    } finally {
      $("#busy").hidden = true;
      $("#file").value = ""; // so choosing the same photo again runs again
    }
  }

  function render(r) {
    $("#stub-note").hidden = !r.stub;
    $("#ms").textContent = r.ms ? "· " + Math.round(r.ms) + " ms in your browser" : "";
    $("#preds").innerHTML = Object.keys(NAMES).map((h) => `
      <div>
        <div class="pred-k">${NAMES[h]}</div>
        <div class="pred-v"><span>${esc(r[h][0].label)}</span><span>${pct(r[h][0].p)}</span></div>
        <div class="bar"><div style="width:${r[h][0].p * 100}%"></div></div>
      </div>`).join("");
    $("#result").hidden = false;

    const heat = $("#heat");
    heat.innerHTML = "";
    const heads = Object.keys(r.heatmaps || {});
    $("#heat-card").hidden = heads.length === 0;
    for (const h of heads) {
      const fig = document.createElement("figure");
      fig.appendChild(r.heatmaps[h]);
      const cap = document.createElement("figcaption");
      cap.innerHTML = `<span>${NAMES[h]}: ${esc(r[h][0].label)}</span><b>${pct(r.focus[h] || 0)}</b>`;
      fig.appendChild(cap);
      heat.appendChild(fig);
    }
  }

  // {id: [articleType, masterCategory]} for every catalogue product (made by build_catalog_embeddings.py)
  let metaCache = null;
  async function catalogMeta() {
    if (!metaCache) {
      const res = await fetch("ai/catalog_meta.json");
      if (!res.ok) throw new Error("catalog_meta.json " + res.status);
      metaCache = await res.json();
    }
    return metaCache;
  }
  const GROUP = { Apparel: "clothing", Footwear: "footwear", Accessories: "accessories" };
  function tierLine(type, used) {
    const parts = [type + " first"];
    if (used[1]) parts.push("then other " + (GROUP[used.master] || "items in the same category"));
    if (used[2]) parts.push("then other items");
    return parts.join(", ") + ", each ranked by how alike they look to the model";
  }

  /** Primary: visual similarity (model embedding vs catalogue embeddings, in the browser).
   *  Fallback: rank by the four predicted tags (api/match.php) if the catalogue files cannot load. */
  async function loadMatches(r) {
    const tags = {};
    for (const h of Object.keys(NAMES)) tags[h] = r[h][0].label;
    const tagRes = await fetch("api/match.php?" + new URLSearchParams(tags));
    if (!tagRes.ok) throw new Error("store search failed");
    const { typeInStore, items: tagItems } = await tagRes.json();

    // When the model is fairly sure of the type (>= SURE) and we sell it, rank the WHOLE catalogue by
    // similarity and fill the slots in tiers: (1) same articleType, (2) same masterCategory (e.g. other
    // footwear), (3) anything else; similarity order inside each tier. Otherwise pure similarity + a notice.
    const SURE = 0.5, SHOW = 24;
    const sureType = typeInStore && r.articleType[0].p >= SURE;
    let items = null, used = [];
    try {
      if (r.stub || !r.embedding) throw new Error("no embedding");
      let ids;
      if (sureType) {
        const meta = await catalogMeta();
        const near = await LensAI.similar(r.embedding, Object.keys(meta).length);
        const master = (Object.values(meta).find((v) => v[0] === tags.articleType) || [])[1];
        const tiers = [[], [], []];
        for (const n of near) {
          const v = meta[n.id];
          tiers[!v ? 2 : v[0] === tags.articleType ? 0 : v[1] === master ? 1 : 2].push(n.id);
        }
        ids = tiers.flat().slice(0, SHOW);
        let left = SHOW;
        used = tiers.map((t) => { const k = Math.min(t.length, left); left -= k; return k; });
        used.master = master;
      } else {
        ids = (await LensAI.similar(r.embedding, SHOW)).map((n) => n.id);
      }
      const res = await fetch("api/products.php?ids=" + ids.join(","));
      if (!res.ok) throw new Error("product lookup failed");
      items = await res.json();
      if (!items.length) throw new Error("no products");
    } catch (e) {
      console.warn("visual similarity unavailable, using tag match:", e);
      items = null;
    }

    const visual = items !== null;
    const read = `${tags.baseColour} ${tags.articleType} for ${tags.gender}, ${tags.usage}`;
    $("#matches-title").textContent = visual ? "Visually similar in our store" : "Matching items in our store";
    $("#match-basis").textContent = !typeInStore
      ? `No matching items in our store: we don't sell ${tags.articleType}. ` + (visual
          ? "Showing the items that look most like your photo instead."
          : `Showing items that match on colour (${tags.baseColour}), gender (${tags.gender}) and occasion (${tags.usage}) instead.`)
      : visual
        ? (sureType ? tierLine(tags.articleType, used) : "Ranked by how alike they look to the model")
          + ` (its 1,280-number fingerprint of each photo). The model read your photo as ${read}.`
        : `Ranked by matching ${read}.`;
    if (!visual) items = tagItems;

    // low confidence on the type usually means the photo is unlike our catalogue photos (worn, top-down, cluttered)
    $("#match-hint").hidden = r.articleType[0].p >= SURE;
    $("#match-hint-p").textContent = Math.round(r.articleType[0].p * 100) + "%";
    // raw similarity scores are not shown: cosine values of these embeddings are low even for close matches
    // and read as "weak" to a visitor; the ORDER is what matters
    $("#matches").innerHTML = items.length ? items.map((p) => {
      return `
      <a class="pcard" href="product.php?id=${p.id}">
        <img loading="lazy" src="${esc(p.image)}" alt="${esc(p.name)}">
        <div class="pc-body"><div class="pc-name">${esc(p.name)}</div>
        <div class="pc-meta">${esc(p.articleType)} · ${esc(p.baseColour || "")}</div>
        <div class="pc-foot"><b>${esc(p.price)}</b>${p.inStock ? "" : '<span class="tag muted">Out of stock</span>'}</div></div>
      </a>`;
    }).join("") : '<p class="empty">No matching items in the store.</p>';
    $("#matches-block").hidden = false;
  }

  function showErr(m) { const e = $("#err"); e.textContent = m; e.hidden = false; }

  const drop = $("#drop");
  $("#file").addEventListener("change", (e) => handle(e.target.files[0]));
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", (e) => handle(e.dataTransfer.files[0]));
})();
