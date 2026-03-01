const INDEX_URL = "./data/reports_index.json";

const CATEGORY_ORDER = ["world", "business", "technology", "sports", "science"];

const CATEGORY_LABELS = {
  world: "World",
  business: "Business",
  technology: "Technology",
  sports: "Sports",
  science: "Science",
};

let indexData = null;
let currentDate = null;
let currentCategory = "world";
let currentReport = null;

function el(id){ return document.getElementById(id); }

function fmtScore(x){
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return (Math.round(x * 1000) / 1000).toFixed(3);
}

function cacheBust(url){
  const u = new URL(url, window.location.href);
  u.searchParams.set("_ts", Date.now());
  return u.toString();
}

async function fetchJson(url){
  const r = await fetch(cacheBust(url), { cache: "no-store" });
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
  return await r.json();
}

function setStatus(text){
  el("status").textContent = text;
}

function setError(text){
  el("error").textContent = text;
  el("error").style.display = text ? "block" : "none";
}

function buildTabs(){
  const tabs = el("tabs");
  tabs.innerHTML = "";

  for (const key of CATEGORY_ORDER){
    const b = document.createElement("button");
    b.className = "tab" + (key === currentCategory ? " active" : "");
    b.textContent = CATEGORY_LABELS[key] ?? key;
    b.onclick = () => {
      currentCategory = key;
      buildTabs();
      render();
    };
    tabs.appendChild(b);
  }
}

function populateDates(){
  const sel = el("dateSelect");
  sel.innerHTML = "";

  if (!indexData?.dates?.length){
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "No reports yet";
    sel.appendChild(opt);
    sel.disabled = true;
    return;
  }

  sel.disabled = false;

  for (const d of indexData.dates){
    const opt = document.createElement("option");
    opt.value = d.date;
    opt.textContent = d.date;
    sel.appendChild(opt);
  }

  sel.value = currentDate;
  sel.onchange = async () => {
    currentDate = sel.value;
    await loadReport(currentDate);
    render();
  };
}

async function loadIndex(){
  setError("");
  setStatus("Loading report index…");
  try{
    indexData = await fetchJson(INDEX_URL);
    currentDate = indexData.latest_date || (indexData.dates?.[0]?.date ?? null);
    populateDates();
    setStatus(currentDate ? `Latest report: ${currentDate}` : "No reports yet.");
  } catch (e){
    indexData = { latest_date: null, dates: [] };
    currentDate = null;
    populateDates();
    setStatus("No reports yet.");
    setError("Could not load reports index. Run the pipeline to generate your first report.");
  }
}

async function loadReport(dateKey){
  if (!dateKey) return;
  setError("");
  setStatus(`Loading report: ${dateKey}…`);
  try{
    currentReport = await fetchJson(`./data/reports/${dateKey}.json`);
    setStatus(`Loaded report: ${dateKey}`);
  } catch (e){
    currentReport = null;
    setError("Could not load the selected report JSON. It may not exist yet.");
    setStatus("Report not available.");
  }
}

function findItemUrl(headline){
  if (!currentReport) return null;
  const items = currentReport.categories?.[currentCategory]?.items || [];
  const h = (headline || "").toLowerCase();
  for (const it of items){
    if (!it?.title) continue;
    const t = it.title.toLowerCase();
    if (t === h || t.includes(h) || h.includes(t)){
      return it.url;
    }
  }
  return null;
}

function render(){
  buildTabs();

  const container = el("content");
  container.innerHTML = "";

  if (!currentDate){
    container.innerHTML = `
      <div class="card">
        <h2>No reports yet</h2>
        <p class="muted">Run <code>python pipeline/run_daily.py</code> locally, or trigger the GitHub Action to generate your first daily report.</p>
      </div>
    `;
    return;
  }

  if (!currentReport){
    container.innerHTML = `
      <div class="card">
        <h2>Report missing</h2>
        <p class="muted">The JSON for <strong>${currentDate}</strong> isn't available. Try a different date or rerun the pipeline.</p>
      </div>
    `;
    return;
  }

  const cat = currentReport.categories?.[currentCategory];
  if (!cat){
    container.innerHTML = `
      <div class="card">
        <h2>Category not available</h2>
        <p class="muted">No data for <strong>${CATEGORY_LABELS[currentCategory]}</strong> on <strong>${currentDate}</strong>.</p>
      </div>
    `;
    return;
  }

  const src = cat.source || {};
  const sent = cat.sentiment || {};
  const rep = cat.ai_report || {};
  const items = cat.items || [];

  const keyThemes = (rep.key_themes || []).map(t => `<span class="pill">${escapeHtml(t)}</span>`).join("");
  const caveats = (rep.caveats || []).map(c => `<li>${escapeHtml(c)}</li>`).join("");

  const notable = (rep.notable_headlines || []).map(n => {
    const url = findItemUrl(n.headline);
    const head = escapeHtml(n.headline || "");
    const link = url ? `<a href="${escapeAttr(url)}" target="_blank" rel="noopener">${head}</a>` : head;
    return `
      <div class="item">
        <div>${link} <span class="badge"><strong>${escapeHtml(n.signal || "Unclear")}</strong></span></div>
        <div class="sum">${escapeHtml(n.why_it_matters || "")}</div>
      </div>
    `;
  }).join("");

  const allHeadlines = items.map(it => {
    const title = escapeHtml(it.title || "");
    const url = escapeAttr(it.url || "#");
    const pub = it.published ? escapeHtml(it.published) : "—";
    const sum = it.summary ? escapeHtml(it.summary) : "";
    return `
      <div class="item">
        <a href="${url}" target="_blank" rel="noopener">${title}</a>
        <div class="meta">Published: ${pub} • Source: ${escapeHtml(it.source || "")}</div>
        ${sum ? `<div class="sum">${sum}</div>` : ""}
      </div>
    `;
  }).join("");

  const outlook = rep.future_outlook || {};
  const out_72 = (outlook.next_24_72_hours || []).map(x => `<li>${escapeHtml(x)}</li>`).join("");
  const out_4w = (outlook.next_1_4_weeks || []).map(x => `<li>${escapeHtml(x)}</li>`).join("");
  const watch = (outlook.watch_list || []).map(x => `<li>${escapeHtml(x)}</li>`).join("");

  container.innerHTML = `
    <div class="grid">
      <div class="card">
        <h2>${escapeHtml(cat.title)} Report</h2>
        <div class="muted">
          Source: <a href="${escapeAttr(src.site_url || "#")}" target="_blank" rel="noopener">${escapeHtml(src.site_name || "")}</a>
          • Feed: <a href="${escapeAttr(src.feed_url || "#")}" target="_blank" rel="noopener">RSS</a>
        </div>

        <div class="badges">
          <span class="badge"><strong>Sentiment:</strong> ${escapeHtml(sent.label || "—")}</span>
          <span class="badge"><strong>Score:</strong> ${fmtScore(sent.score)}</span>
          <span class="badge"><strong>Outlook confidence:</strong> ${escapeHtml(outlook.confidence || "—")}</span>
        </div>

        <div class="hr"></div>

        <h3>Executive summary</h3>
        <p>${escapeHtml(rep.summary || "")}</p>

        <h3>Key themes</h3>
        <div class="pills">${keyThemes || '<span class="muted">—</span>'}</div>

        <h3>Notable headlines (with why it matters)</h3>
        ${notable || '<p class="muted">—</p>'}

        <div class="hr"></div>

        <h3>Future outlook</h3>
        <div class="split3">
          <div class="card" style="box-shadow:none">
            <h3>Next 24–72 hours</h3>
            <ul>${out_72 || '<li>—</li>'}</ul>
          </div>
          <div class="card" style="box-shadow:none">
            <h3>Next 1–4 weeks</h3>
            <ul>${out_4w || '<li>—</li>'}</ul>
          </div>
          <div class="card" style="box-shadow:none">
            <h3>Watch list</h3>
            <ul>${watch || '<li>—</li>'}</ul>
          </div>
        </div>

        <h3>Caveats</h3>
        <ul>${caveats || '<li>—</li>'}</ul>
      </div>

      <div class="card">
        <h2>All headlines</h2>
        <div class="muted">Click any headline to read the original source.</div>
        <div class="hr"></div>
        ${allHeadlines || '<p class="muted">—</p>'}
      </div>
    </div>

    <div class="footer">
      Generated at (UTC): <strong>${escapeHtml(currentReport.generated_at_utc || "—")}</strong>
      • Timezone used for report date: <strong>${escapeHtml(currentReport.timezone || "—")}</strong>
      • Model: <strong>${escapeHtml(currentReport.model || "—")}</strong>
    </div>
  `;
}

function escapeHtml(str){
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(str){
  return escapeHtml(str).replaceAll("`", "&#096;");
}

async function init(){
  el("refreshBtn").onclick = async () => {
    await loadIndex();
    if (currentDate) await loadReport(currentDate);
    render();
  };

  await loadIndex();
  if (currentDate) await loadReport(currentDate);
  buildTabs();
  render();
}

init().catch(err => {
  setError("Unexpected error loading the app.");
  console.error(err);
});
