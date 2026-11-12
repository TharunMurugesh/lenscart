/* "Our AI model" page: Try it (upload) and Test mode (held-out test images). */
(function () {
  const R = window.MODEL_REPORT, ROOT = window.SITE_ROOT || "";
  const HEADS = Object.keys(R.heads);
  const $ = (s) => document.querySelector(s);
  const pct = (p) => (p * 100).toFixed(1) + "%";
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------------------------------------------------------------- Try it
  function headCard(h, r) {
    const card = document.createElement("div");
    card.className = "m-head";
    card.innerHTML = `<div class="m-head-t">${esc(R.heads[h])}<span>focus ${Math.round(r.focus[h] * 100)}%</span></div>`;
    card.appendChild(r.heatmaps[h]);
    const list = document.createElement("ol");
    list.className = "m-bars";
    list.innerHTML = r[h].map((x) =>
      `<li><span class="m-bar-l">${esc(x.label)}</span><span class="m-bar"><i style="width:${(x.p * 100).toFixed(1)}%"></i></span><span class="m-bar-v">${pct(x.p)}</span></li>`).join("");
    card.appendChild(list);
    return card;
  }

  async function runTry(file) {
    const status = $("#tryStatus"), out = $("#tryOut");
    if (!file || !file.type.startsWith("image/")) { status.textContent = "Please choose an image file."; return; }
    status.textContent = "Loading the model…";
    const img = new Image();
    img.onload = async () => {
      try {
        await LensAI.load();
        status.textContent = "Analysing…";
        const r = await LensAI.analyze(img);
        out.innerHTML = "";
        const first = document.createElement("div");
        first.className = "m-head";
        first.innerHTML = '<div class="m-head-t">What the model sees<span>224 × 224</span></div>';
        first.appendChild(r.input);
        out.appendChild(first);
        HEADS.forEach((h) => out.appendChild(headCard(h, r)));
        status.textContent = `Done in ${Math.round(r.ms)} ms, in your browser.`;
      } catch (e) {
        status.textContent = "The model could not run here: " + e.message;
      } finally {
        URL.revokeObjectURL(img.src);
      }
    };
    img.src = URL.createObjectURL(file);
  }

  const drop = $("#tryDrop"), file = $("#tryFile");
  if (drop) {
    file.addEventListener("change", () => runTry(file.files[0]));
    ["dragover", "dragenter"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
    drop.addEventListener("drop", (e) => runTry(e.dataTransfer.files[0]));
  }

  // ---------------------------------------------------------------- Test mode
  let current = null, seen = 0, right = {}, total = {};
  HEADS.forEach((h) => { right[h] = 0; total[h] = 0; });

  function cell(truth, pred, conf) {
    if (pred == null) return '<td class="m-dim">–</td>';
    const ok = truth == null ? "" : pred === truth ? "ok" : "bad";
    return `<td><span class="m-pill ${ok}">${esc(pred)}</span> <small>${pct(conf)}</small></td>`;
  }

  function render(live) {
    const rows = HEADS.map((h) => {
      const t = current[h], lv = live && live[h] ? live[h][0] : null;
      return `<tr><td>${esc(R.heads[h])}</td><td>${t.true == null ? '<span class="m-dim">unknown</span>' : esc(t.true)}</td>`
        + cell(t.true, t.pred, t.conf) + (lv ? cell(t.true, lv.label, lv.p) : '<td class="m-dim">–</td>') + "</tr>";
    }).join("");
    $("#testTable tbody").innerHTML = rows;
  }

  function score() {
    const parts = HEADS.map((h) => total[h] ? `${esc(R.heads[h])} ${right[h]}/${total[h]}` : null).filter(Boolean);
    $("#testScore").textContent = seen ? `This session: ${parts.join(" · ")}` : "";
  }

  function next() {
    current = R.test[Math.floor(Math.random() * R.test.length)];
    $("#testImg").src = ROOT + current.image;
    seen++;
    HEADS.forEach((h) => {
      const t = current[h];
      if (t.true != null) { total[h]++; if (t.pred === t.true) right[h]++; }
    });
    render(null);
    score();
  }

  async function live() {
    const btn = $("#testLive");
    btn.disabled = true;
    try {
      await LensAI.load();
      const r = await LensAI.analyze($("#testImg"));
      render(r);
    } catch (e) {
      $("#testScore").textContent = "Live run failed: " + e.message;
    } finally {
      btn.disabled = false;
    }
  }

  if ($("#testNext") && R.test.length) {
    $("#testNext").addEventListener("click", next);
    $("#testLive").addEventListener("click", live);
    next();
  }

  // ---------------------------------------------------------------- confusion matrix switcher
  document.querySelectorAll("[data-cm]").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll("[data-cm]").forEach((x) => x.classList.toggle("on", x === b));
    $("#cmImg").src = ROOT + "img/model/cm_" + b.dataset.cm + ".png";
  }));
})();
