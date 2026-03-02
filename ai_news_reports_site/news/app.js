const INDEX_URL = "./data/reports_index.json";
const SITE_URL = "https://YOUR_DOMAIN";

const CATEGORY_ORDER = ["world", "business", "technology", "sports", "science"];

const CATEGORY_LABELS = {
  world: "World",
  business: "Business",
  technology: "Technology",
  sports: "Sports",
  science: "Science",
};

const PREF_KEYS = {
  mode: "tldr_mode",
  layout: "tldr_layout",
};

let indexData = null;
let currentDate = null;
let currentCategory = "world";
let currentReport = null;
let isLoading = false;
let headlineQuery = "";

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
  const node = el("error");
  node.textContent = text || "";
  node.hidden = !text;
}

function readPref(key, fallback){
  try{
    const v = localStorage.getItem(key);
    return (v === null || v === undefined || v === "") ? fallback : v;
  }catch(_){
    return fallback;
  }
}

function writePref(key, value){
  try{ localStorage.setItem(key, String(value)); }catch(_){ /* ignore */ }
}

function applyUiPrefs(){
  const root = document.documentElement;

  // Force Brutalism always (no style switching).
  root.dataset.style = "brutal";

  const mode = readPref(PREF_KEYS.mode, root.dataset.mode || "dark");
  const layout = readPref(PREF_KEYS.layout, root.dataset.layout || "classic");
  root.dataset.mode = mode;
  root.dataset.layout = layout;
}

function syncUiControls(){
  const root = document.documentElement;

  const modeBtn = el("modeToggle");
  if (modeBtn){
    const isDark = (root.dataset.mode || "dark") === "dark";
    modeBtn.setAttribute("aria-pressed", String(isDark));
    modeBtn.textContent = `Dark mode: ${isDark ? "On" : "Off"}`;
  }

  const layoutBtn = el("layoutToggle");
  if (layoutBtn){
    const isBroken = (root.dataset.layout || "classic") === "broken";
    layoutBtn.setAttribute("aria-pressed", String(isBroken));
    layoutBtn.textContent = `Broken grid: ${isBroken ? "On" : "Off"}`;
  }
}

function initUiControls(){
  applyUiPrefs();
  syncUiControls();

  const modeBtn = el("modeToggle");
  if (modeBtn){
    modeBtn.onclick = () => {
      const root = document.documentElement;
      const now = (root.dataset.mode || "dark") === "dark" ? "light" : "dark";
      root.dataset.mode = now;
      writePref(PREF_KEYS.mode, now);
      syncUiControls();
    };
  }

  const layoutBtn = el("layoutToggle");
  if (layoutBtn){
    layoutBtn.onclick = () => {
      const root = document.documentElement;
      const now = (root.dataset.layout || "classic") === "broken" ? "classic" : "broken";
      root.dataset.layout = now;
      writePref(PREF_KEYS.layout, now);
      syncUiControls();
    };
  }
}

function setLoading(flag){
  isLoading = !!flag;
  document.documentElement.classList.toggle("is-loading", isLoading);
}

function initProgressBar(){
  const bar = el("progressBar");
  if (!bar) return;
  function update(){
    const scrolled = window.scrollY;
    const total = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = (total > 0 ? (scrolled / total) * 100 : 0) + "%";
  }
  window.addEventListener("scroll", update, { passive: true });
  update();
}

function animateCards(){
  document.querySelectorAll("#content .card:not(.skeleton)").forEach((card, i) => {
    setTimeout(() => card.classList.add("is-visible"), i * 80);
  });
}

function readUrlParams(){
  const p = new URLSearchParams(window.location.search);
  const d = p.get("date");
  const c = p.get("cat");
  if (d) currentDate = d;
  if (c && CATEGORY_ORDER.includes(c)) currentCategory = c;
}

function pushUrlState(){
  if (!currentDate) return;
  const url = new URL(window.location.href);
  url.searchParams.set("date", currentDate);
  url.searchParams.set("cat", currentCategory);
  history.replaceState(null, "", url.toString());
}

function updateMeta(catData){
  const date = currentDate || "";
  const catLabel = CATEGORY_LABELS[currentCategory] || currentCategory;
  const summary = catData?.ai_report?.summary || "";
  const desc = summary
    ? summary.slice(0, 155) + (summary.length > 155 ? "\u2026" : "")
    : `${catLabel} news for ${date} \u2014 AI-generated daily briefing.`;
  const title = `${catLabel} \u00b7 ${date} | TL;DR News`;
  const pageUrl = `${SITE_URL}/news/reports.html?date=${date}&cat=${currentCategory}`;

  document.title = title;

  const can = document.getElementById("metaCanonical");
  if (can) can.href = pageUrl;

  const metaDesc = document.querySelector('meta[name="description"]');
  if (metaDesc) metaDesc.content = desc;

  const ogTitle = document.getElementById("metaOgTitle");
  const ogDesc = document.getElementById("metaOgDesc");
  const ogUrl = document.getElementById("metaOgUrl");
  if (ogTitle) ogTitle.setAttribute("content", title);
  if (ogDesc) ogDesc.setAttribute("content", desc);
  if (ogUrl) ogUrl.setAttribute("content", pageUrl);

  const twTitle = document.getElementById("metaTwTitle");
  const twDesc = document.getElementById("metaTwDesc");
  if (twTitle) twTitle.setAttribute("content", title);
  if (twDesc) twDesc.setAttribute("content", desc);

  const jsonLdPage = document.getElementById("jsonLdPage");
  if (jsonLdPage && currentReport){
    const themes = catData?.ai_report?.key_themes || [];
    const ld = {
      "@context": "https://schema.org",
      "@type": "WebPage",
      "name": title,
      "url": pageUrl,
      "description": desc,
      "datePublished": date,
      "dateModified": currentReport.generated_at_utc || date,
      "publisher": {
        "@type": "NewsMediaOrganization",
        "name": "TL;DR News",
        "url": SITE_URL
      },
      "about": themes.map(t => ({ "@type": "Thing", "name": t })),
      "keywords": [catLabel, "AI news", "daily briefing", "news summary", date].join(", ")
    };
    jsonLdPage.textContent = JSON.stringify(ld);
  }
}

function buildTabs(){
  const tabs = el("tabs");
  tabs.innerHTML = "";

  for (const key of CATEGORY_ORDER){
    const b = document.createElement("button");
    b.type = "button";
    b.setAttribute("role", "tab");
    b.className = "tab" + (key === currentCategory ? " active" : "");
    b.textContent = CATEGORY_LABELS[key] ?? key;
    b.setAttribute("aria-selected", String(key === currentCategory));
    b.onclick = () => {
      currentCategory = key;
      buildTabs();
      render();
      animateCards();
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
    renderSkeleton();
    await loadReport(currentDate);
    render();
    animateCards();
  };
}

async function loadIndex(){
  setError("");
  setStatus("Loading report index…");
  setLoading(true);
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
  } finally {
    setLoading(false);
  }
}

async function loadReport(dateKey){
  if (!dateKey) return;
  setError("");
  setStatus(`Loading report: ${dateKey}…`);
  setLoading(true);
  try{
    currentReport = await fetchJson(`./data/reports/${dateKey}.json`);
    setStatus(`Loaded report: ${dateKey}`);
  } catch (e){
    currentReport = null;
    setError("Could not load the selected report JSON. It may not exist yet.");
    setStatus("Report not available.");
  } finally {
    setLoading(false);
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

function buildSentimentKpi(sent, outlook){
  const score = sent.score ?? 0;
  const pct = ((Math.min(1, Math.max(-1, score)) + 1) / 2) * 100;
  const fillColor = score > 0.1 ? "var(--positive)" : score < -0.1 ? "var(--negative)" : "var(--neutral)";
  const labelClass = (sent.label || "").toLowerCase().includes("positive") ? "badge--positive"
                   : (sent.label || "").toLowerCase().includes("negative") ? "badge--negative"
                   : "badge--neutral";
  return `
    <span class="badge ${labelClass}">${escapeHtml(sent.label || "—")}</span>
    <div class="sentiment-bar" title="Sentiment score: ${fmtScore(score)}">
      <div class="sentiment-fill" style="width:${pct}%;background:${fillColor}"></div>
    </div>
    <span class="badge"><strong>Score:</strong> ${fmtScore(sent.score)}</span>
    <span class="badge"><strong>Confidence:</strong> ${escapeHtml(outlook.confidence || "—")}</span>
  `;
}

function render(){
  buildTabs();

  const container = el("content");
  container.innerHTML = "";

  if (isLoading){
    renderSkeleton();
    return;
  }

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

  const keyThemes = normalizeList(rep.key_themes).map(t => `<span class="pill">${escapeHtml(t)}</span>`).join("");
  const caveats = normalizeList(rep.caveats).map(c => `<li>${escapeHtml(c)}</li>`).join("");
  const notableItems = normalizeNotableHeadlines(rep.notable_headlines, items);

  const notable = notableItems.map(n => {
    const url = findItemUrl(n.headline);
    const head = escapeHtml(n.headline || "");
    const link = url ? `<a href="${escapeAttr(url)}" target="_blank" rel="noopener">${head}</a>` : head;
    const sigLower = (n.signal || "").toLowerCase();
    const sigClass = sigLower.includes("positive") ? "badge--positive"
                   : sigLower.includes("negative") ? "badge--negative"
                   : "badge--neutral";
    return `
      <div class="item">
        <div>${link} <span class="badge ${sigClass}">${escapeHtml(n.signal || "Unclear")}</span></div>
        <div class="sum">${escapeHtml(n.why_it_matters || "")}</div>
      </div>
    `;
  }).join("");

  const filteredItems = filterItems(items, headlineQuery);

  const allHeadlines = filteredItems.map(it => {
    const title = escapeHtml(it.title || "");
    const url = escapeAttr(it.url || "#");
    const pub = it.published ? escapeHtml(it.published) : "—";
    const sum = it.summary ? escapeHtml(stripHtml(it.summary)) : "";
    return `
      <div class="item">
        <a href="${url}" target="_blank" rel="noopener">${title}</a>
        <div class="meta">Published: ${pub} • Source: ${escapeHtml(it.source || "")}</div>
        ${sum ? `<div class="sum">${sum}</div>` : ""}
      </div>
    `;
  }).join("");

  const outlook = normalizeOutlook(rep.future_outlook);
  const out_72 = outlook.next_24_72_hours.map(x => `<li>${escapeHtml(x)}</li>`).join("");
  const out_4w = outlook.next_1_4_weeks.map(x => `<li>${escapeHtml(x)}</li>`).join("");
  const watch = outlook.watch_list.map(x => `<li>${escapeHtml(x)}</li>`).join("");

  container.innerHTML = `
    <div class="grid">
      <div class="card">
        <h2>${escapeHtml(cat.title)} Report</h2>
        <div class="muted">
          Source: <a href="${escapeAttr(src.site_url || "#")}" target="_blank" rel="noopener">${escapeHtml(src.site_name || "")}</a>
          • Feed: <a href="${escapeAttr(src.feed_url || "#")}" target="_blank" rel="noopener">RSS</a>
        </div>

        <div class="kpi">
          ${buildSentimentKpi(sent, outlook)}
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
          <div class="card card--flat">
            <h3>Next 24–72 hours</h3>
            <ul>${out_72 || '<li>—</li>'}</ul>
          </div>
          <div class="card card--flat">
            <h3>Next 1–4 weeks</h3>
            <ul>${out_4w || '<li>—</li>'}</ul>
          </div>
          <div class="card card--flat">
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

        <div class="search" role="search" aria-label="Search headlines">
          <input id="searchInput" type="search" placeholder="Search headlines…" value="${escapeAttr(headlineQuery)}" />
        </div>
        <div class="hr"></div>
        ${allHeadlines || `<p class="muted">${headlineQuery ? "No matches for your search." : "—"}</p>`}
      </div>
    </div>

    <div class="footer">
      Generated at (UTC): <strong>${escapeHtml(currentReport.generated_at_utc || "—")}</strong>
      • Timezone used for report date: <strong>${escapeHtml(currentReport.timezone || "—")}</strong>
      • Model: <strong>${escapeHtml(currentReport.model || "—")}</strong>
    </div>
  `;

  const search = el("searchInput");
  if (search){
    search.oninput = (e) => {
      headlineQuery = String(e.target.value || "");
      render();
    };
  }

  const catData = currentReport?.categories?.[currentCategory];
  pushUrlState();
  updateMeta(catData);
}

function filterItems(items, query){
  const q = String(query || "").trim().toLowerCase();
  if (!q) return items;
  return (items || []).filter(it => {
    const t = String(it?.title || "").toLowerCase();
    const s = String(stripHtml(it?.summary || "")).toLowerCase();
    const src = String(it?.source || "").toLowerCase();
    return t.includes(q) || s.includes(q) || src.includes(q);
  });
}

function renderSkeleton(){
  const container = el("content");
  container.innerHTML = `
    <div class="grid">
      <div class="card skeleton">
        <div class="sk-line sk-title"></div>
        <div class="sk-line sk-wide"></div>
        <div class="sk-line sk-mid"></div>
        <div class="hr"></div>
        <div class="sk-line sk-short"></div>
        <div class="sk-block"></div>
        <div class="sk-block"></div>
      </div>
      <div class="card skeleton">
        <div class="sk-line sk-title"></div>
        <div class="sk-line sk-wide"></div>
        <div class="sk-block"></div>
        <div class="sk-block"></div>
        <div class="sk-block"></div>
      </div>
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

function normalizeList(value){
  if (Array.isArray(value)) return value.filter(Boolean).map(v => String(v));
  if (typeof value === "string" && value.trim()) return [value.trim()];
  return [];
}

function normalizeOutlook(value){
  if (!value || typeof value !== "object" || Array.isArray(value)){
    return {
      next_24_72_hours: normalizeList(value),
      next_1_4_weeks: [],
      watch_list: [],
      confidence: "—",
    };
  }

  return {
    next_24_72_hours: normalizeList(value.next_24_72_hours),
    next_1_4_weeks: normalizeList(value.next_1_4_weeks),
    watch_list: normalizeList(value.watch_list),
    confidence: value.confidence || "—",
  };
}

function normalizeNotableHeadlines(value, fallbackItems = []){
  if (Array.isArray(value)){
    return value
      .map(normalizeNotableItem)
      .filter(Boolean);
  }

  if (value && typeof value === "object"){
    const nested = value.items || value.headlines || value.notable || value.results;
    if (Array.isArray(nested)){
      return nested
        .map(normalizeNotableItem)
        .filter(Boolean);
    }

    const single = normalizeNotableItem(value);
    if (single) return [single];
  }

  if (typeof value === "string" && value.trim()){
    return [{
      headline: value.trim(),
      why_it_matters: "",
      signal: "Unclear",
    }];
  }

  return fallbackItems
    .slice(0, 8)
    .filter(it => it?.title)
    .map(it => ({
      headline: it.title,
      why_it_matters: stripHtml(it.summary || "").slice(0, 240),
      signal: "Unclear",
    }));
}

function normalizeNotableItem(value){
  if (!value) return null;
  if (typeof value === "string"){
    return {
      headline: value,
      why_it_matters: "",
      signal: "Unclear",
    };
  }

  if (typeof value !== "object") return null;

  const headline = String(
    value.headline ?? value.title ?? value.name ?? ""
  ).trim();

  if (!headline) return null;

  return {
    headline,
    why_it_matters: String(value.why_it_matters ?? value.reason ?? value.summary ?? "").trim(),
    signal: String(value.signal || "Unclear").trim() || "Unclear",
  };
}

function stripHtml(str){
  const raw = String(str ?? "");
  if (!raw) return "";

  const parser = new DOMParser();
  const doc = parser.parseFromString(raw, "text/html");
  const text = (doc.body?.textContent || "")
    .replace(/\s+/g, " ")
    .trim();

  if (text) return text;

  return raw
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&quot;/gi, '"')
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

async function init(){
  readUrlParams();
  initUiControls();
  initProgressBar();

  renderSkeleton();

  el("refreshBtn").onclick = async () => {
    headlineQuery = "";
    renderSkeleton();
    await loadIndex();
    if (currentDate) await loadReport(currentDate);
    render();
    animateCards();
  };

  await loadIndex();
  if (currentDate) await loadReport(currentDate);
  buildTabs();
  render();
  animateCards();
}

init().catch(err => {
  setError("Unexpected error loading the app.");
  console.error(err);
});
