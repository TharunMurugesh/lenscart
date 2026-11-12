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

  async function loadMatches(r) {
    const tags = {};
    for (const h of Object.keys(NAMES)) tags[h] = r[h][0].label;
    const res = await fetch("api/match.php?" + new URLSearchParams(tags));
    if (!res.ok) throw new Error("store search failed");
    const items = await res.json();
    $("#match-basis").textContent = `Ranked by matching ${tags.baseColour} ${tags.articleType} for ${tags.gender}, ${tags.usage}.`;
    $("#matches").innerHTML = items.length ? items.map((p) => `
      <a class="pcard" href="product.php?id=${p.id}">
        <img loading="lazy" src="${esc(p.image)}" alt="${esc(p.name)}">
        <div class="pc-body"><div class="pc-name">${esc(p.name)}</div>
        <div class="pc-meta">${esc(p.articleType)} · ${esc(p.baseColour || "")}</div>
        <div class="pc-foot"><b>${esc(p.price)}</b>${p.inStock ? "" : '<span class="tag muted">Out of stock</span>'}</div></div>
      </a>`).join("") : '<p class="empty">No matching items in the store.</p>';
    $("#matches-block").hidden = false;
  }

  function showErr(m) { const e = $("#err"); e.textContent = m; e.hidden = false; }

  const drop = $("#drop");
  $("#file").addEventListener("change", (e) => handle(e.target.files[0]));
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", (e) => handle(e.dataTransfer.files[0]));
})();
