const INDEX_URL = "./data/reports_index.json";

const CATEGORY_ORDER = ["world", "business", "technology", "sports", "science"];

const CATEGORY_LABELS = {
  world:      "World",
  business:   "Business",
  technology: "Technology",
  sports:     "Sports",
  science:    "Science",
};

const PREF_KEYS = {
  mode: "tldr_mode",
};

let indexData       = null;
let currentDate     = null;
let currentCategory = "world";
let currentReport   = null;
let isLoading       = false;
let headlineQuery   = "";
let sentimentCache  = {};  // { "YYYY-MM-DD": { category: score } }

/* ── Utilities ── */

function el(id){ return document.getElementById(id); }

function fmtScore(x){
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return (Math.round(x * 1000) / 1000).toFixed(3);
}

function cacheBust(url){
  const u = new URL(url, document.baseURI);
  u.searchParams.set("_ts", Date.now());
  return u.toString();
}

async function fetchJson(url){
  const r = await fetch(cacheBust(url), { cache: "no-store" });
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
  return r.json();
}

function setStatus(text){ el("status").textContent = text; }

function setError(text){
  const node = el("error");
  node.textContent = text || "";
  node.hidden = !text;
}

function readPref(key, fallback){
  try{
    const v = localStorage.getItem(key);
    return (v === null || v === undefined || v === "") ? fallback : v;
  }catch(_){ return fallback; }
}

function writePref(key, value){
  try{ localStorage.setItem(key, String(value)); }catch(_){}
}

/* ── Live clock ── */

function startClock(){
  const node = el("live-clock");
  if (!node) return;
  function tick(){
    const now  = new Date();
    const date = now.toLocaleDateString("en-US", { weekday:"short", month:"short", day:"numeric", year:"numeric" });
    const time = now.toLocaleTimeString("en-US", { hour:"2-digit", minute:"2-digit", second:"2-digit" });
    node.textContent = `${date} · ${time}`;
  }
  tick();
  setInterval(tick, 1000);
}

/* ── Scroll progress bar ── */

function initScrollProgress(){
  const bar = el("pg-bar");
  if (!bar) return;
  const scrollEl = el("contentScroll");
  const update = () => {
    let pct = 0;
    if (scrollEl && scrollEl.scrollHeight > scrollEl.clientHeight){
      const max = scrollEl.scrollHeight - scrollEl.clientHeight;
      pct = max > 0 ? Math.round((scrollEl.scrollTop / max) * 100) : 0;
    } else {
      const scrollTop = window.scrollY || document.documentElement.scrollTop;
      const docH      = document.documentElement.scrollHeight - window.innerHeight;
      pct = docH > 0 ? Math.round((scrollTop / docH) * 100) : 0;
    }
    bar.style.setProperty("--pg", pct + "%");
  };
  if (scrollEl) scrollEl.addEventListener("scroll", update, { passive: true });
  window.addEventListener("scroll", update, { passive: true });
}

/* ── Sidebar (mobile drawer) ── */

function initSidebar(){
  const sidebar   = el("sidebar");
  const hamburger = el("hamburger");
  const closeBtn  = el("sidebarClose");
  const overlay   = el("navOverlay");

  function openSidebar(){
    if (!sidebar) return;
    sidebar.classList.add("open");
    overlay?.classList.add("visible");
    hamburger?.setAttribute("aria-expanded", "true");
  }

  function closeSidebar(){
    if (!sidebar) return;
    sidebar.classList.remove("open");
    overlay?.classList.remove("visible");
    hamburger?.setAttribute("aria-expanded", "false");
  }

  if (hamburger) hamburger.onclick = openSidebar;
  if (closeBtn)  closeBtn.onclick  = closeSidebar;
  if (overlay)   overlay.onclick   = closeSidebar;

  // Expose close so tab clicks can collapse the drawer on mobile
  window._closeSidebar = closeSidebar;
}

/* ── Dark / light mode ── */

function applyUiPrefs(){
  const root = document.documentElement;
  const mode = readPref(PREF_KEYS.mode, root.dataset.mode || "dark");
  root.dataset.mode = mode;
}

function syncUiControls(){
  const root   = document.documentElement;
  const btn    = el("modeToggle");
  if (!btn) return;
  const isDark = (root.dataset.mode || "dark") === "dark";
  btn.setAttribute("aria-pressed", String(isDark));
  btn.textContent = `${isDark ? "☾" : "☀"} ${isDark ? "Dark" : "Light"} mode`;
}

function initUiControls(){
  applyUiPrefs();
  syncUiControls();

  const btn = el("modeToggle");
  if (btn){
    btn.onclick = () => {
      const root = document.documentElement;
      const next = (root.dataset.mode || "dark") === "dark" ? "light" : "dark";
      root.dataset.mode = next;
      writePref(PREF_KEYS.mode, next);
      syncUiControls();
    };
  }
}

/* ── Topbar ── */

function updateTopbar(){
  const catEl  = el("topbarCat");
  const dateEl = el("topbarDate");
  if (catEl)  catEl.textContent  = CATEGORY_LABELS[currentCategory] || currentCategory;
  if (dateEl) dateEl.textContent = currentDate || "—";
}

/* ── Dynamic meta description ── */

function updateMeta(){
  if (!currentReport) return;
  const cat = currentReport.categories?.[currentCategory];
  if (!cat) return;
  const takeaway = cat.ai_report?.key_takeaway || "";
  if (!takeaway) return;
  const label = CATEGORY_LABELS[currentCategory] || currentCategory;
  const desc = `${label}: ${takeaway}`;
  const metaDesc = el("metaDesc");
  const ogDesc = el("ogDesc");
  if (metaDesc) metaDesc.setAttribute("content", desc);
  if (ogDesc) ogDesc.setAttribute("content", desc);
  document.title = `${label} — ${currentDate} · TL;DR News`;
}

/* ── Loading state ── */

function setLoading(flag){
  isLoading = !!flag;
  document.documentElement.classList.toggle("is-loading", isLoading);
}

/* ── Tabs ── */

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
      updateTopbar();
      render();
      // Close mobile drawer after selecting a category
      if (window.innerWidth <= 960) window._closeSidebar?.();
    };
    tabs.appendChild(b);
  }
}

/* ── Date selector ── */

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
    updateTopbar();
    renderSkeleton();
    await loadReport(currentDate);
    render();
  };
}

/* ── Data loading ── */

async function loadIndex(){
  setError("");
  setStatus("Loading report index…");
  setLoading(true);
  try{
    indexData   = await fetchJson(INDEX_URL);
    currentDate = indexData.latest_date || (indexData.dates?.[0]?.date ?? null);
    populateDates();
    updateTopbar();
    setStatus(currentDate ? `Latest report: ${currentDate}` : "No reports yet.");
  }catch(e){
    indexData   = { latest_date: null, dates: [] };
    currentDate = null;
    populateDates();
    updateTopbar();
    setStatus("No reports yet.");
    setError("Could not load reports index. Run the pipeline to generate your first report.");
  }finally{
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
    setStatus(`Loaded: ${dateKey}`);
  }catch(e){
    currentReport = null;
    setError("Could not load the selected report JSON. It may not exist yet.");
    setStatus("Report not available.");
  }finally{
    setLoading(false);
  }
}

/* ── Helpers ── */

function findItemUrl(headline){
  if (!currentReport) return null;
  const items = currentReport.categories?.[currentCategory]?.items || [];
  const h = (headline || "").toLowerCase();
  for (const it of items){
    if (!it?.title) continue;
    const t = it.title.toLowerCase();
    if (t === h || t.includes(h) || h.includes(t)) return it.url;
  }
  return null;
}

/* Convert sentiment score (-1…1) to CSS percentage and color variable */
function sentimentStyle(score){
  if (score === null || score === undefined || Number.isNaN(score)){
    return { pct: "50%", color: "var(--muted)" };
  }
  const pct = Math.round(((score + 1) / 2) * 100);
  let color;
  if      (score > 0.1)  color = "var(--positive)";
  else if (score < -0.1) color = "var(--negative)";
  else                   color = "var(--accent)";
  return { pct: pct + "%", color };
}

/* Lower-case signal name → badge modifier class */
function signalClass(signal){
  const s = String(signal || "").toLowerCase().trim();
  if (s === "opportunity") return "badge--opportunity";
  if (s === "risk")        return "badge--risk";
  return "badge--unclear";
}

function filterItems(items, query){
  const q = String(query || "").trim().toLowerCase();
  if (!q) return items;
  return (items || []).filter(it => {
    const t   = String(it?.title   || "").toLowerCase();
    const s   = String(stripHtml(it?.summary || "")).toLowerCase();
    const src = String(it?.source  || "").toLowerCase();
    return t.includes(q) || s.includes(q) || src.includes(q);
  });
}

/* Trigger stagger reveal animation on rendered items */
function triggerReveal(){
  const cards = document.querySelectorAll(".content .card");
  cards.forEach((card, i) => {
    card.classList.add("reveal", `reveal-${Math.min(i + 1, 8)}`);
  });
  const items = document.querySelectorAll(".content .item");
  items.forEach((item, i) => {
    item.style.animationDelay = `${0.1 + i * 0.03}s`;
    item.classList.add("reveal");
  });
}

/* ── Sentiment trend chart ── */

async function loadSentimentHistory(category, maxDays = 30) {
  if (!indexData?.dates?.length) return [];
  const dates = indexData.dates.slice(0, maxDays);
  const points = [];

  // Load reports we haven't cached yet
  const toFetch = dates.filter(d => !(d.date in sentimentCache));
  await Promise.all(toFetch.map(async (d) => {
    try {
      const report = await fetchJson(`./data/reports/${d.date}.json`);
      const entry = {};
      for (const [key, cat] of Object.entries(report.categories || {})) {
        const score = cat?.sentiment?.score;
        entry[key] = (score !== null && score !== undefined && !Number.isNaN(score)) ? score : null;
      }
      sentimentCache[d.date] = entry;
    } catch (_) {
      sentimentCache[d.date] = {};
    }
  }));

  // Collect points in chronological order (oldest first)
  for (let i = dates.length - 1; i >= 0; i--) {
    const d = dates[i].date;
    const score = sentimentCache[d]?.[category] ?? null;
    if (score !== null) {
      points.push({ date: d, score });
    }
  }
  return points;
}

function renderSentimentChart(points) {
  if (!points || points.length < 2) return "";

  const W = 320, H = 80, PAD = 4;
  const scores = points.map(p => p.score);
  const minS = Math.min(...scores, -0.3);
  const maxS = Math.max(...scores, 0.3);
  const range = maxS - minS || 0.6;

  const xStep = (W - PAD * 2) / (points.length - 1);
  const coords = points.map((p, i) => ({
    x: PAD + i * xStep,
    y: PAD + (1 - (p.score - minS) / range) * (H - PAD * 2),
    date: p.date,
    score: p.score,
  }));

  const polyline = coords.map(c => `${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");

  // Zero line
  const zeroY = PAD + (1 - (0 - minS) / range) * (H - PAD * 2);

  // Dots for first, last, and extremes
  const dotIndices = new Set([0, coords.length - 1]);
  let minIdx = 0, maxIdx = 0;
  scores.forEach((s, i) => { if (s < scores[minIdx]) minIdx = i; if (s > scores[maxIdx]) maxIdx = i; });
  dotIndices.add(minIdx);
  dotIndices.add(maxIdx);

  const dots = [...dotIndices].map(i => {
    const c = coords[i];
    const color = c.score > 0.1 ? "var(--positive)" : c.score < -0.1 ? "var(--negative)" : "var(--accent)";
    return `<circle cx="${c.x.toFixed(1)}" cy="${c.y.toFixed(1)}" r="3" fill="${color}" stroke="var(--surface)" stroke-width="1.5"/>`;
  }).join("");

  const latest = points[points.length - 1];
  const oldest = points[0];
  const delta = latest.score - oldest.score;
  const arrow = delta > 0.02 ? "&#9650;" : delta < -0.02 ? "&#9660;" : "&#9644;";
  const deltaColor = delta > 0.02 ? "var(--positive)" : delta < -0.02 ? "var(--negative)" : "var(--muted2)";

  return `
    <div class="trend-chart">
      <div class="trend-chart__header">
        <span class="trend-chart__label">Sentiment Trend</span>
        <span class="trend-chart__delta" style="color:${deltaColor}">${arrow} ${delta >= 0 ? "+" : ""}${delta.toFixed(3)} over ${points.length} days</span>
      </div>
      <svg viewBox="0 0 ${W} ${H}" class="trend-chart__svg" aria-label="Sentiment trend over ${points.length} days">
        <line x1="${PAD}" y1="${zeroY.toFixed(1)}" x2="${W - PAD}" y2="${zeroY.toFixed(1)}" stroke="var(--border2)" stroke-width="0.5" stroke-dasharray="3,3"/>
        <polyline points="${polyline}" fill="none" stroke="var(--accent)" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>
        ${dots}
      </svg>
      <div class="trend-chart__range">
        <span>${escapeHtml(oldest.date)}</span>
        <span>${escapeHtml(latest.date)}</span>
      </div>
    </div>
  `;
}

/* ── Main render ── */

function render(){
  buildTabs();
  updateMeta();
  const container = el("content");
  container.innerHTML = "";

  if (isLoading){
    renderSkeleton();
    return;
  }

  if (!currentDate){
    container.innerHTML = `
      <div class="card reveal reveal-1">
        <h2>No reports yet</h2>
        <p class="muted">Run <code>python -m pipeline.run_daily</code> locally, or trigger the GitHub Action to generate your first daily report.</p>
      </div>
    `;
    return;
  }

  if (!currentReport){
    container.innerHTML = `
      <div class="card reveal reveal-1">
        <h2>Report missing</h2>
        <p class="muted">The JSON for <strong>${currentDate}</strong> isn't available. Try a different date or re-run the pipeline.</p>
      </div>
    `;
    return;
  }

  const cat = currentReport.categories?.[currentCategory];
  if (!cat){
    container.innerHTML = `
      <div class="card reveal reveal-1">
        <h2>Category not available</h2>
        <p class="muted">No data for <strong>${CATEGORY_LABELS[currentCategory]}</strong> on <strong>${currentDate}</strong>.</p>
      </div>
    `;
    return;
  }

  const src   = cat.source    || {};
  const sent  = cat.sentiment || {};
  const rep   = cat.ai_report || {};
  const items = cat.items     || [];
  const trending = currentReport.trending_topics || [];

  /* Sentiment gauge */
  const { pct: sentPct, color: sentColor } = sentimentStyle(sent.score);

  /* Key themes */
  const keyThemes = normalizeList(rep.key_themes)
    .map(t => `<span class="pill">${escapeHtml(t)}</span>`).join("");

  /* Caveats */
  const caveats = normalizeList(rep.caveats)
    .map(c => `<li>${escapeHtml(c)}</li>`).join("");

  /* Notable headlines */
  const notableItems = normalizeNotableHeadlines(rep.notable_headlines, items);
  const notable = notableItems.map(n => {
    const url  = findItemUrl(n.headline);
    const head = escapeHtml(n.headline || "");
    const link = url
      ? `<a href="${escapeAttr(url)}" target="_blank" rel="noopener">${head}</a>`
      : head;
    const sc = signalClass(n.signal);
    return `
      <div class="item">
        <div>${link} <span class="badge ${escapeAttr(sc)}">${escapeHtml(n.signal || "Unclear")}</span></div>
        <div class="sum">${escapeHtml(n.why_it_matters || "")}</div>
      </div>
    `;
  }).join("");

  /* All headlines */
  const filteredItems = filterItems(items, headlineQuery);
  const allHeadlines  = filteredItems.map(it => {
    const title = escapeHtml(it.title || "");
    const url   = escapeAttr(it.url || "#");
    const pub   = it.published ? escapeHtml(it.published) : "—";
    const sum   = it.summary ? escapeHtml(stripHtml(it.summary)) : "";
    return `
      <div class="item">
        <a href="${url}" target="_blank" rel="noopener">${title}</a>
        <div class="meta">Published: ${pub} &middot; ${escapeHtml(it.source || "")}</div>
        ${sum ? `<div class="sum">${sum}</div>` : ""}
      </div>
    `;
  }).join("");

  /* Future outlook */
  const outlook = normalizeOutlook(rep.future_outlook);
  const out_72  = outlook.next_24_72_hours.map(x => `<li>${escapeHtml(x)}</li>`).join("");
  const out_4w  = outlook.next_1_4_weeks.map(x   => `<li>${escapeHtml(x)}</li>`).join("");
  const watch   = outlook.watch_list.map(x        => `<li>${escapeHtml(x)}</li>`).join("");

  /* Reading-time estimate (rough: 200 wpm) */
  const wordCount = (rep.summary || "").split(/\s+/).length
    + notableItems.reduce((a, n) => a + (n.why_it_matters || "").split(/\s+/).length, 0);
  const readMins  = Math.max(1, Math.round(wordCount / 200));

  // Load sentiment trend in background
  const trendPlaceholderId = `trend-${Date.now()}`;

  container.innerHTML = `
    <div class="grid">

      <!-- ── Left: AI Report ── -->
      <div class="card">
        <h2>${escapeHtml(cat.title)} Report
          <span style="font-family:var(--mono);font-size:11px;font-weight:400;color:var(--muted);margin-left:10px;letter-spacing:.04em;">~${readMins} min read</span>
        </h2>

        <div class="source-line">
          Source: <a href="${escapeAttr(src.site_url || "#")}" target="_blank" rel="noopener">${escapeHtml(src.site_name || "")}</a>
          &nbsp;&middot;&nbsp;
          <a href="${escapeAttr(src.feed_url || "#")}" target="_blank" rel="noopener">RSS feed ↗</a>
          &nbsp;&middot;&nbsp;
          <a href="./${escapeAttr(currentDate)}/${escapeAttr(currentCategory)}.html">Full report ↗</a>
        </div>

        ${trending.length ? `
        <div class="trending">
          <span class="trending__label">Trending across categories</span>
          <div class="trending__pills">${trending.slice(0, 6).map(t => `<span class="pill pill--trending">${escapeHtml(t)}</span>`).join("")}</div>
        </div>` : ""}

        <div class="kpi">
          <span class="badge">Sentiment: <strong>${escapeHtml(sent.label || "—")}</strong></span>
          <span class="badge">Score: <strong>${fmtScore(sent.score)}</strong></span>
          <span class="badge">Confidence: <strong>${escapeHtml(outlook.confidence || "—")}</strong></span>
        </div>
        <div class="sentiment-bar">
          <div class="sentiment-bar__fill" style="--pct:${sentPct}; --bar-color:${sentColor}"></div>
        </div>
        <div id="${trendPlaceholderId}"></div>

        <div class="hr"></div>

        ${rep.key_takeaway ? `
        <div class="key-takeaway">
          <span class="key-takeaway__label">Key Takeaway</span>
          <span class="key-takeaway__text">${escapeHtml(rep.key_takeaway)}</span>
        </div>
        <div class="hr"></div>
        ` : ""}

        <h3>Executive Summary</h3>
        <p>${escapeHtml(rep.summary || "No summary available.")}</p>

        <h3>Key Themes</h3>
        <div class="pills">${keyThemes || '<span class="muted" style="padding:10px 18px;display:block;">—</span>'}</div>

        <h3>Notable Headlines</h3>
        ${notable || '<p class="muted">—</p>'}

        <div class="hr"></div>

        <h3>Future Outlook</h3>
        <div class="split3">
          <div class="card card--flat">
            <h3>Next 24–72 h</h3>
            <ul>${out_72 || "<li>—</li>"}</ul>
          </div>
          <div class="card card--flat">
            <h3>Next 1–4 weeks</h3>
            <ul>${out_4w || "<li>—</li>"}</ul>
          </div>
          <div class="card card--flat">
            <h3>Watch list</h3>
            <ul>${watch || "<li>—</li>"}</ul>
          </div>
        </div>

        <h3>Caveats</h3>
        <ul>${caveats || "<li>—</li>"}</ul>
      </div>

      <!-- ── Right: All headlines ── -->
      <div class="card">
        <h2>All Headlines <span style="font-family:var(--mono);font-size:11px;font-weight:400;color:var(--muted);margin-left:6px;">${items.length} items</span></h2>
        <div class="search" role="search" aria-label="Search headlines">
          <input id="searchInput" type="search" placeholder="Filter headlines…" value="${escapeAttr(headlineQuery)}" />
        </div>
        <div class="hr"></div>
        ${allHeadlines || `<p class="muted" style="padding:12px 18px;">${headlineQuery ? "No matches." : "—"}</p>`}
      </div>

    </div>

  `;

  const search = el("searchInput");
  if (search){
    search.oninput = (e) => {
      const pos = e.target.selectionEnd;
      headlineQuery = String(e.target.value || "");
      render();
      const newSearch = el("searchInput");
      if (newSearch){
        newSearch.focus();
        newSearch.setSelectionRange(pos, pos);
      }
    };
  }

  triggerReveal();

  // Async: load sentiment trend chart
  loadSentimentHistory(currentCategory, 30).then(points => {
    const placeholder = document.getElementById(trendPlaceholderId);
    if (placeholder && points.length >= 2) {
      placeholder.innerHTML = renderSentimentChart(points);
    }
  }).catch(() => {});
}

/* ── Skeleton loader ── */

function renderSkeleton(){
  const container = el("content");
  container.innerHTML = `
    <div class="grid">
      <div class="card">
        <div class="sk-line sk-title" style="margin-top:18px;"></div>
        <div class="sk-line sk-wide"></div>
        <div class="sk-line sk-mid"></div>
        <div class="hr"></div>
        <div class="sk-line sk-short"></div>
        <div class="sk-block"></div>
        <div class="sk-block"></div>
        <div class="sk-line sk-wide"></div>
        <div class="sk-block"></div>
      </div>
      <div class="card">
        <div class="sk-line sk-title" style="margin-top:18px;"></div>
        <div class="sk-line sk-wide"></div>
        <div class="sk-block"></div>
        <div class="sk-block"></div>
        <div class="sk-block"></div>
        <div class="sk-block"></div>
      </div>
    </div>
  `;
}

/* ── Escape helpers ── */

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

/* ── Normalize helpers ── */

function normalizeList(value){
  if (Array.isArray(value)) return value.filter(Boolean).map(v => String(v));
  if (typeof value === "string" && value.trim()) return [value.trim()];
  return [];
}

function normalizeOutlook(value){
  if (!value || typeof value !== "object" || Array.isArray(value)){
    return {
      next_24_72_hours: normalizeList(value),
      next_1_4_weeks:   [],
      watch_list:       [],
      confidence:       "—",
    };
  }
  return {
    next_24_72_hours: normalizeList(value.next_24_72_hours),
    next_1_4_weeks:   normalizeList(value.next_1_4_weeks),
    watch_list:       normalizeList(value.watch_list),
    confidence:       value.confidence || "—",
  };
}

function normalizeNotableHeadlines(value, fallbackItems = []){
  if (Array.isArray(value)){
    return value.map(normalizeNotableItem).filter(Boolean);
  }
  if (value && typeof value === "object"){
    const nested = value.items || value.headlines || value.notable || value.results;
    if (Array.isArray(nested)) return nested.map(normalizeNotableItem).filter(Boolean);
    const single = normalizeNotableItem(value);
    if (single) return [single];
  }
  if (typeof value === "string" && value.trim()){
    return [{ headline: value.trim(), why_it_matters: "", signal: "Unclear" }];
  }
  return fallbackItems
    .slice(0, 8)
    .filter(it => it?.title)
    .map(it => ({
      headline:        it.title,
      why_it_matters:  stripHtml(it.summary || "").slice(0, 240),
      signal:          "Unclear",
    }));
}

function normalizeNotableItem(value){
  if (!value) return null;
  if (typeof value === "string"){
    return { headline: value, why_it_matters: "", signal: "Unclear" };
  }
  if (typeof value !== "object") return null;
  const headline = String(value.headline ?? value.title ?? value.name ?? "").trim();
  if (!headline) return null;
  return {
    headline,
    why_it_matters: String(value.why_it_matters ?? value.reason ?? value.summary ?? "").trim(),
    signal:         String(value.signal || "Unclear").trim() || "Unclear",
  };
}

function stripHtml(str){
  const raw = String(str ?? "");
  if (!raw) return "";
  const parser = new DOMParser();
  const doc    = parser.parseFromString(raw, "text/html");
  const text   = (doc.body?.textContent || "").replace(/\s+/g, " ").trim();
  if (text) return text;
  return raw
    .replace(/&nbsp;/gi, " ").replace(/&amp;/gi, "&").replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">").replace(/&#39;|&apos;/gi, "'").replace(/&quot;/gi, '"')
    .replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

/* ── Init ── */

async function init(){
  startClock();
  initScrollProgress();
  initSidebar();
  initUiControls();

  renderSkeleton();

  el("refreshBtn").onclick = async () => {
    headlineQuery = "";
    renderSkeleton();
    await loadIndex();
    if (currentDate) await loadReport(currentDate);
    render();
  };

  await loadIndex();
  if (currentDate) await loadReport(currentDate);
  buildTabs();
  updateTopbar();
  render();
}

init().catch(err => {
  setError("Unexpected error loading the app.");
  console.error(err);
});
