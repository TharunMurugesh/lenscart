const $ = (s) => document.querySelector(s);
const HEAD_NAMES = { articleType: "Type", baseColour: "Colour", gender: "Gender", usage: "Usage" };
const pct = (v, d = 0) => (v == null ? "n/a" : (100 * v).toFixed(d) + "%");
const icons = () => window.lucide && lucide.createIcons();
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* ---------- tabs ---------- */
document.querySelectorAll(".tab").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === b));
    document.querySelectorAll(".view").forEach((v) => (v.hidden = v.id !== "view-" + b.dataset.view));
    // the banner is about live predictions; Test mode reads the trained model's saved predictions
    $("#placeholder-banner").hidden = !(placeholder && b.dataset.view === "analyze");
    if (b.dataset.view === "test" && !testLoaded) nextTest();
  })
);

/* ---------- status ---------- */
let placeholder = false;
fetch("/api/status").then((r) => r.json()).then((s) => {
  placeholder = s.placeholder;
  $("#model-chip span").textContent = s.placeholder ? `${s.backbone} · untrained heads` : `${s.backbone} · trained`;
  $("#placeholder-banner").hidden = !s.placeholder;
}).catch(() => ($("#model-chip span").textContent = "Server not reachable"));

/* ---------- analyze ---------- */
const drop = $("#drop");
$("#file").addEventListener("change", (e) => e.target.files[0] && run(e.target.files[0]));
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => e.dataTransfer.files[0] && run(e.dataTransfer.files[0]));

async function run(file) {
  $("#error").hidden = true;
  $("#busy").hidden = false;
  $("#results").hidden = true;
  $("#steps").hidden = false;
  document.querySelectorAll("#steps li").forEach((li) => { li.classList.remove("done"); li.querySelector("em").textContent = ""; });
  const fd = new FormData();
  fd.append("file", file);
  try {
    const r = await fetch("/api/analyze", { method: "POST", body: fd });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || r.statusText);
    render(d);
  } catch (err) {
    $("#error").hidden = false;
    $("#error").innerHTML = `<i data-lucide="circle-alert"></i><span>${esc(err.message)}</span>`;
    icons();
  } finally {
    $("#busy").hidden = true;
  }
}

function render(d) {
  drop.classList.add("compact");
  placeholder = d.placeholder;
  $("#placeholder-banner").hidden = !d.placeholder;
  document.querySelectorAll("#steps li").forEach((li) => {
    const t = d.timings[li.dataset.step];
    li.classList.add("done");
    li.querySelector("em").textContent = t != null ? t.toFixed(2) + " s" : "";
  });

  $("#img-original").src = d.original;
  $("#img-cleaned").src = d.cleaned;
  $("#mask-share").textContent = pct(d.mask_share);
  $("#mask-method").textContent = d.mask_method === "u2net"
    ? "U²-Net (rembg)" : "white-background threshold (U²-Net model not on this laptop)";

  $("#preds").innerHTML = Object.entries(d.heads).map(([h, v]) => `
    <div>
      <div class="pred-head">${HEAD_NAMES[h]}</div>
      <div class="pred-top"><span>${esc(v.top[0].label)}</span><span>${pct(v.top[0].prob)}</span></div>
      ${v.top.slice(1).map((t) => `
        <div class="bar-row"><span>${esc(t.label)}</span><div class="bar"><div style="width:${100 * t.prob}%"></div></div><b>${pct(t.prob)}</b></div>`).join("")}
    </div>`).join("");

  $("#heat").innerHTML = Object.entries(d.heads).map(([h, v]) => `
    <figure>
      <img src="${v.heatmap}" alt="Heat map for ${HEAD_NAMES[h]}">
      <div class="cap"><span>${HEAD_NAMES[h]}: ${esc(v.top[0].label)}</span><b title="Garment-focus score">${pct(v.focus)}</b></div>
    </figure>`).join("");

  $("#palette").innerHTML = d.palette.length
    ? d.palette.map((c) => `<div class="sw"><i style="background:${c.hex}"></i><code>${c.hex}</code><b>${pct(c.share)}</b></div>`).join("")
    : `<p class="note">No garment pixels found by M2.</p>`;
  $("#m1-colour").textContent = d.heads.baseColour.top[0].label;

  $("#results").hidden = false;
  icons();
}

/* ---------- test mode ---------- */
let testLoaded = false;
let score = { right: 0, total: 0 };

async function nextTest() {
  testLoaded = true;
  const r = await fetch("/api/test/next");
  const d = await r.json();
  if (!r.ok) {
    $("#test-empty").hidden = false;
    $("#test-body").hidden = true;
    $("#test-empty-msg").textContent = d.detail;
    return;
  }
  $("#test-empty").hidden = true;
  $("#test-body").hidden = false;
  $("#test-img").src = d.image || "";
  $("#test-img").alt = d.image ? "Unseen test image" : "Image file not on this laptop";
  $("#test-id").textContent = `Product ${d.id} · one of ${d.total.toLocaleString()} test images`;
  $("#test-rows").innerHTML = Object.entries(d.heads).map(([h, v]) => {
    score.total++; if (v.correct) score.right++;
    return `<tr class="${v.correct ? "ok" : "no"}"><td>${HEAD_NAMES[h]}</td><td>${esc(v.true)}</td>
      <td>${esc(v.pred)}${v.conf != null ? ` <span class="muted">${pct(v.conf)}</span>` : ""}</td>
      <td><i data-lucide="${v.correct ? "circle-check" : "circle-x"}"></i></td></tr>`;
  }).join("");
  showScore();
  icons();
}
function showScore() {
  $("#score-pct").textContent = score.total ? pct(score.right / score.total) : "–";
  $("#score-raw").textContent = `${score.right} of ${score.total} answers right`;
}
$("#test-next").addEventListener("click", nextTest);
$("#test-reset").addEventListener("click", () => { score = { right: 0, total: 0 }; showScore(); });

icons();
