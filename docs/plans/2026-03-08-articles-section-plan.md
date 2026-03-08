# Articles Section Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a separate articles page where manually written markdown articles can be published and rendered client-side.

**Architecture:** A new `articles.html` page shares the same sidebar/shell as `reports.html`. Articles are markdown files with YAML frontmatter stored in `news/articles/`. An `articles_index.json` lists all articles. Client-side JS fetches the index, renders a listing view, and uses marked.js (CDN) to render individual articles. Note: marked.js output is used with DOMPurify for XSS protection.

**Tech Stack:** Vanilla JS, HTML5, CSS3, marked.js (CDN), DOMPurify (CDN), same design tokens from `style.css`

---

### Task 1: Create articles index

**Files:**
- Create: `ai_news_reports_site/news/articles/articles_index.json`

**Step 1: Create empty index**

```json
[]
```

**Step 2: Commit**

```bash
git add ai_news_reports_site/news/articles/articles_index.json
git commit -m "Add empty articles index"
```

---

### Task 2: Create articles.html

**Files:**
- Create: `ai_news_reports_site/news/articles.html`

Same shell as `reports.html` but with:
- Title: "Articles - TL;DR News"
- Sidebar navigation links (Reports / Articles) instead of category tabs and date picker
- Category filter dropdown
- Loads marked.js and DOMPurify from CDN
- Loads `articles.js` instead of `app.js`
- Topbar shows "Articles"

**Step 1: Commit**

```bash
git add ai_news_reports_site/news/articles.html
git commit -m "Add articles.html page"
```

---

### Task 3: Create articles.js

**Files:**
- Create: `ai_news_reports_site/news/articles.js`

Handles:
- Loading `articles_index.json` (with cache-busting `_ts` param)
- Rendering article listing cards (title, date, author, category badge)
- Category filter
- Clicking a card fetches the `.md` file, parses frontmatter, renders markdown via `marked.parse()` sanitized with `DOMPurify.sanitize()`
- Back button to return to listing
- URL query param support (`?article=slug` for direct links)
- Dark/light mode toggle (shared `localStorage` key `tldr_mode`)
- Mobile sidebar toggle
- Scroll progress bar
- Live clock

All dynamic HTML insertion uses `textContent` for user-provided strings or `DOMPurify.sanitize()` for rendered markdown.

**Step 1: Commit**

```bash
git add ai_news_reports_site/news/articles.js
git commit -m "Add articles.js with listing and markdown rendering"
```

---

### Task 4: Add article styles to style.css

**Files:**
- Modify: `ai_news_reports_site/news/style.css`

Append before the responsive media queries section:

- `.article-card` — hover effects (border glow, lift)
- `.article-card__meta` — flex row with badge + date + author
- `.btn--back` — inline back button
- `.article-body` — rendered markdown styles (headings, paragraphs, lists, blockquotes, code blocks, images, hr)

All styles use existing CSS variables for consistency.

**Step 1: Commit**

```bash
git add ai_news_reports_site/news/style.css
git commit -m "Add article styles to style.css"
```

---

### Task 5: Add navigation links to reports.html sidebar

**Files:**
- Modify: `ai_news_reports_site/news/reports.html`

Add a "Navigate" section before the Categories section with Reports (active) and Articles links.

**Step 1: Commit**

```bash
git add ai_news_reports_site/news/reports.html
git commit -m "Add Articles navigation link to reports sidebar"
```

---

### Task 6: Manual verification

**Step 1: Serve locally**

```bash
python -m http.server 8080 --directory ai_news_reports_site
```

Open `http://localhost:8080/news/articles.html` and verify:
- Empty state shows "No articles yet"
- Sidebar navigation works between Reports and Articles
- Dark/light mode toggle works
- Mobile sidebar works

**Step 2: Test with a sample article**

Create a test markdown file and add it to the index. Verify:
- Card appears in listing
- Click renders full markdown
- Back button returns to listing
- Category filter works
- Direct link via `?article=slug` works

**Step 3: Push**

```bash
git push
```
