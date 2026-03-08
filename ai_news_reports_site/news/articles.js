/* ══════════════════════════════════════════════════════════════
   articles.js — TL;DR News · Articles listing & markdown reader
   ══════════════════════════════════════════════════════════════ */

const ARTICLES_INDEX_URL = "./articles/articles_index.json";

const CATEGORY_LABELS = {
  world:      "World",
  business:   "Business",
  technology: "Technology",
  sports:     "Sports",
  science:    "Science",
};

const CATEGORY_BADGE = {
  world:      "badge--risk",
  business:   "badge--opportunity",
  technology: "badge--opportunity",
  sports:     "badge--unclear",
  science:    "badge--opportunity",
};

const PREF_KEYS = { mode: "tldr_mode" };

let articlesIndex   = [];
let currentFilter   = "all";
let currentArticle  = null;   // slug when viewing an article

/* ── Utilities ── */

function el(id) { return document.getElementById(id); }

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function cacheBust(url) {
  const u = new URL(url, window.location.href);
  u.searchParams.set("_ts", Date.now());
  return u.toString();
}

async function fetchText(url) {
  const r = await fetch(cacheBust(url), { cache: "no-store" });
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
  return r.text();
}

async function fetchJson(url) {
  const r = await fetch(cacheBust(url), { cache: "no-store" });
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
  return r.json();
}

function readPref(key, fallback) {
  try {
    const v = localStorage.getItem(key);
    return (v === null || v === undefined || v === "") ? fallback : v;
  } catch (_) { return fallback; }
}

function writePref(key, value) {
  try { localStorage.setItem(key, String(value)); } catch (_) {}
}

/* ── Live clock ── */

function startClock() {
  const node = el("live-clock");
  if (!node) return;
  function tick() {
    const now  = new Date();
    const date = now.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
    const time = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    node.textContent = `${date} · ${time}`;
  }
  tick();
  setInterval(tick, 30000);
}

/* ── Scroll progress bar ── */

function initScrollProgress() {
  const bar = el("pg-bar");
  if (!bar) return;
  const scrollEl = el("contentScroll");
  const update = () => {
    let pct = 0;
    if (scrollEl && scrollEl.scrollHeight > scrollEl.clientHeight) {
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

function initSidebar() {
  const sidebar   = el("sidebar");
  const hamburger = el("hamburger");
  const closeBtn  = el("sidebarClose");
  const overlay   = el("navOverlay");

  function openSidebar() {
    if (!sidebar) return;
    sidebar.classList.add("open");
    overlay?.classList.add("visible");
    hamburger?.setAttribute("aria-expanded", "true");
  }

  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove("open");
    overlay?.classList.remove("visible");
    hamburger?.setAttribute("aria-expanded", "false");
  }

  if (hamburger) hamburger.onclick = openSidebar;
  if (closeBtn)  closeBtn.onclick  = closeSidebar;
  if (overlay)   overlay.onclick   = closeSidebar;

  window._closeSidebar = closeSidebar;
}

/* ── Dark / light mode ── */

function applyUiPrefs() {
  const root = document.documentElement;
  const mode = readPref(PREF_KEYS.mode, root.dataset.mode || "dark");
  root.dataset.mode = mode;
}

function syncUiControls() {
  const root = document.documentElement;
  const btn  = el("modeToggle");
  if (!btn) return;
  const isDark = (root.dataset.mode || "dark") === "dark";
  btn.setAttribute("aria-pressed", String(isDark));
  btn.textContent = `${isDark ? "\u263E" : "\u2600"} ${isDark ? "Dark" : "Light"} mode`;
}

function initUiControls() {
  applyUiPrefs();
  syncUiControls();

  const btn = el("modeToggle");
  if (btn) {
    btn.onclick = () => {
      const root = document.documentElement;
      const next = (root.dataset.mode || "dark") === "dark" ? "light" : "dark";
      root.dataset.mode = next;
      writePref(PREF_KEYS.mode, next);
      syncUiControls();
    };
  }
}

/* ── Skeleton loader ── */

function renderSkeleton() {
  const container = el("content");
  const wrapper = document.createElement("div");
  wrapper.className = "grid";

  const card1 = document.createElement("div");
  card1.className = "card";

  const sk1 = document.createElement("div");
  sk1.className = "sk-line sk-title";
  sk1.style.marginTop = "18px";
  card1.appendChild(sk1);

  const sk2 = document.createElement("div");
  sk2.className = "sk-line sk-wide";
  card1.appendChild(sk2);

  const sk3 = document.createElement("div");
  sk3.className = "sk-line sk-mid";
  card1.appendChild(sk3);

  const hr1 = document.createElement("div");
  hr1.className = "hr";
  card1.appendChild(hr1);

  const sk4 = document.createElement("div");
  sk4.className = "sk-line sk-short";
  card1.appendChild(sk4);

  const sk5 = document.createElement("div");
  sk5.className = "sk-block";
  card1.appendChild(sk5);

  const sk6 = document.createElement("div");
  sk6.className = "sk-block";
  card1.appendChild(sk6);

  wrapper.appendChild(card1);

  const card2 = document.createElement("div");
  card2.className = "card";

  const sk7 = document.createElement("div");
  sk7.className = "sk-line sk-title";
  sk7.style.marginTop = "18px";
  card2.appendChild(sk7);

  const sk8 = document.createElement("div");
  sk8.className = "sk-line sk-wide";
  card2.appendChild(sk8);

  const sk9 = document.createElement("div");
  sk9.className = "sk-block";
  card2.appendChild(sk9);

  const sk10 = document.createElement("div");
  sk10.className = "sk-block";
  card2.appendChild(sk10);

  wrapper.appendChild(card2);

  container.textContent = "";
  container.appendChild(wrapper);
}

/* ── Frontmatter parser ── */

function parseFrontmatter(raw) {
  const text = String(raw || "");
  const match = text.match(/^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$/);
  if (!match) return { meta: {}, body: text };

  const yamlBlock = match[1];
  const body      = match[2];
  const meta      = {};

  for (const line of yamlBlock.split("\n")) {
    const idx = line.indexOf(":");
    if (idx < 0) continue;
    const key = line.slice(0, idx).trim();
    let val   = line.slice(idx + 1).trim();
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    if (key) meta[key] = val;
  }

  return { meta, body };
}

/* ── Listing view ── */

function renderListing() {
  const container = el("content");
  const filtered  = currentFilter === "all"
    ? articlesIndex
    : articlesIndex.filter(a => a.category === currentFilter);

  container.textContent = "";

  if (!filtered.length) {
    const card = document.createElement("div");
    card.className = "card reveal reveal-1";

    const h2 = document.createElement("h2");
    h2.textContent = "No articles yet";
    card.appendChild(h2);

    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "Check back later for long-form analysis and commentary.";
    card.appendChild(p);

    container.appendChild(card);
    return;
  }

  filtered.forEach((article, i) => {
    const revealClass = `card article-card reveal reveal-${Math.min(i + 1, 8)}`;
    const badgeClass  = CATEGORY_BADGE[article.category] || "badge--unclear";
    const catLabel    = CATEGORY_LABELS[article.category] || article.category || "";

    const card = document.createElement("div");
    card.className = revealClass;
    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");
    card.dataset.slug = article.slug;

    const h2 = document.createElement("h2");
    h2.textContent = article.title || "Untitled";
    card.appendChild(h2);

    const metaRow = document.createElement("div");
    metaRow.className = "meta";

    const badge = document.createElement("span");
    badge.className = "badge " + badgeClass;
    badge.textContent = catLabel;
    metaRow.appendChild(badge);

    const metaText = document.createTextNode(" " + (article.date || "") + " \u00B7 " + (article.author || ""));
    metaRow.appendChild(metaText);

    card.appendChild(metaRow);

    card.addEventListener("click", () => openArticle(article.slug));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter") openArticle(article.slug);
    });

    container.appendChild(card);
  });
}

/* ── Article view ── */

async function openArticle(slug) {
  currentArticle = slug;
  updateUrl(slug);

  const scrollEl = el("contentScroll");
  if (scrollEl) scrollEl.scrollTop = 0;

  renderSkeleton();

  try {
    const raw = await fetchText("articles/" + encodeURIComponent(slug) + ".md");
    const { meta, body } = parseFrontmatter(raw);
    renderArticle(meta, body);
  } catch (e) {
    const container = el("content");
    container.textContent = "";

    const card = document.createElement("div");
    card.className = "card reveal reveal-1";

    const h2 = document.createElement("h2");
    h2.textContent = "Article not found";
    card.appendChild(h2);

    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "Could not load the article. It may have been removed or the slug is incorrect.";
    card.appendChild(p);

    container.appendChild(card);
    console.error("Failed to load article:", e);
  }
}

function renderArticle(meta, body) {
  const container = el("content");
  container.textContent = "";

  const wrapper = document.createElement("div");
  wrapper.className = "card reveal reveal-1";

  // Back button
  const backBtn = document.createElement("button");
  backBtn.type = "button";
  backBtn.className = "btn";
  backBtn.textContent = "\u2190 Back to articles";
  backBtn.style.marginBottom = "18px";
  backBtn.addEventListener("click", goBackToListing);
  wrapper.appendChild(backBtn);

  // Title
  const h2 = document.createElement("h2");
  h2.textContent = meta.title || "Untitled";
  wrapper.appendChild(h2);

  // Meta row
  const metaRow = document.createElement("div");
  metaRow.className = "meta";

  const badgeClass = CATEGORY_BADGE[meta.category] || "badge--unclear";
  const catLabel   = CATEGORY_LABELS[meta.category] || meta.category || "";

  const badge = document.createElement("span");
  badge.className = "badge " + badgeClass;
  badge.textContent = catLabel;
  metaRow.appendChild(badge);

  const metaText = document.createTextNode(" " + (meta.date || "") + " \u00B7 " + (meta.author || ""));
  metaRow.appendChild(metaText);

  wrapper.appendChild(metaRow);

  // Divider
  const hr = document.createElement("div");
  hr.className = "hr";
  wrapper.appendChild(hr);

  // Rendered markdown body — DOMPurify.sanitize makes this safe
  const articleBody = document.createElement("div");
  articleBody.className = "article-body";
  articleBody.innerHTML = DOMPurify.sanitize(marked.parse(body || ""));
  wrapper.appendChild(articleBody);

  container.appendChild(wrapper);
}

function goBackToListing() {
  currentArticle = null;
  updateUrl(null);
  renderListing();
}

/* ── URL management ── */

function updateUrl(slug) {
  const url = new URL(window.location.href);
  if (slug) {
    url.searchParams.set("article", slug);
  } else {
    url.searchParams.delete("article");
  }
  history.pushState(null, "", url.toString());
}

function getArticleFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("article") || null;
}

/* ── Category filter ── */

function initCategoryFilter() {
  const select = el("categoryFilter");
  if (!select) return;
  select.addEventListener("change", () => {
    currentFilter = select.value;
    if (!currentArticle) renderListing();
  });
}

/* ── Init ── */

async function init() {
  startClock();
  initScrollProgress();
  initSidebar();
  initUiControls();
  initCategoryFilter();

  renderSkeleton();

  try {
    const data = await fetchJson(ARTICLES_INDEX_URL);
    articlesIndex = Array.isArray(data) ? data : [];
    // Sort newest first
    articlesIndex.sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  } catch (e) {
    articlesIndex = [];
    console.error("Failed to load articles index:", e);
  }

  // Check for direct link via ?article=slug
  const slugParam = getArticleFromUrl();
  if (slugParam) {
    await openArticle(slugParam);
  } else {
    renderListing();
  }
}

// Handle browser back/forward
window.addEventListener("popstate", () => {
  const slug = getArticleFromUrl();
  if (slug) {
    openArticle(slug);
  } else {
    currentArticle = null;
    renderListing();
  }
});

init().catch(err => {
  const container = el("content");
  if (container) {
    container.textContent = "";

    const card = document.createElement("div");
    card.className = "card reveal reveal-1";

    const h2 = document.createElement("h2");
    h2.textContent = "Error";
    card.appendChild(h2);

    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "Unexpected error loading the articles page.";
    card.appendChild(p);

    container.appendChild(card);
  }
  console.error(err);
});
