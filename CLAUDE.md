# CLAUDE.md — TLDR-NEWS Codebase Guide

This file provides guidance for AI assistants working in this repository.

---

## Project Overview

TLDR-NEWS is a fully automated daily news aggregation and reporting system. A GitHub Actions workflow runs every morning, fetches RSS headlines from 5 news sources, uses OpenAI to generate structured AI reports, and deploys the results as a static website via GitHub Pages.

There is no web server, no database, and no build step. The pipeline writes JSON files that vanilla JavaScript reads client-side.

---

## Repository Layout

```
TLDR-NEWS/
├── CLAUDE.md                          # This file
├── .github/
│   └── workflows/
│       └── daily_news_reports.yml     # CI/CD: runs pipeline + deploys Pages
└── ai_news_reports_site/              # Everything that gets served on GitHub Pages
    ├── README.md
    ├── requirements.txt               # Python 3.11 dependencies
    ├── pipeline/                      # Python backend
    │   ├── __init__.py
    │   ├── config.py                  # News source definitions (CATEGORIES dict)
    │   ├── run_daily.py               # Pipeline entry point (run with -m pipeline.run_daily)
    │   └── agents/
    │       ├── __init__.py
    │       ├── base.py                # NewsItem, SentimentResult dataclasses
    │       ├── rss_reader.py          # Fetches + parses RSS feeds
    │       ├── curator.py             # Deduplicates headlines
    │       ├── sentiment.py           # VADER lexicon-based sentiment
    │       ├── report_writer.py       # Main AI report generation (OpenAI structured output)
    │       ├── executive_summary.py   # AI executive summary generation
    │       ├── future_outlook.py      # AI forward-looking analysis
    │       ├── publisher.py           # Writes JSON to disk, maintains index
    │       └── openai_compat.py       # Unified OpenAI API wrapper with fallbacks
    └── news/                          # Static frontend
        ├── index.html                 # Redirects to reports.html
        ├── reports.html              # Main page (loads app.js + style.css)
        ├── app.js                     # All frontend logic (~571 lines, vanilla JS)
        ├── style.css                  # "Brutal" minimalist aesthetic (~343 lines)
        └── data/
            ├── reports_index.json     # Index of available report dates + categories
            └── reports/
                └── YYYY-MM-DD.json   # One JSON file per day (~57 KB each)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Pipeline language | Python 3.11 |
| LLM integration | OpenAI API (`openai` >= 1.40.0) |
| RSS parsing | `feedparser` >= 6.0.11 |
| Sentiment analysis | `vaderSentiment` >= 3.3.2 |
| HTTP client | `requests` >= 2.31.0 |
| Date handling | `python-dateutil` >= 2.9.0 |
| Frontend | Vanilla JS, HTML5, CSS3 — zero npm dependencies |
| Hosting | GitHub Pages (static) |
| CI/CD | GitHub Actions |

---

## Local Development

All pipeline commands must be run from inside `ai_news_reports_site/`:

```bash
cd ai_news_reports_site

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Set required environment variable
export OPENAI_API_KEY="sk-..."

# Optional: override the default model (gpt-4o-mini)
export OPENAI_MODEL="gpt-4o"

# Run the full pipeline
python -m pipeline.run_daily
```

The pipeline works without `OPENAI_API_KEY` (falls back to a deterministic stub report), but AI-generated content will be absent.

Output files are written to `news/data/reports/YYYY-MM-DD.json` and `news/data/reports_index.json`.

To view the frontend locally, serve `ai_news_reports_site/` via any static file server:

```bash
python -m http.server 8080 --directory ai_news_reports_site
# then open http://localhost:8080/news/reports.html
```

---

## Pipeline Architecture

The pipeline is a sequential agent chain. Each agent is a single-responsibility class with a `run()` method.

```
RSS feeds → RssReaderAgent → CuratorAgent → SentimentAgent → ReportWriterAgent → PublisherAgent
```

### Agent Responsibilities

| Agent | File | What it does |
|---|---|---|
| `RssReaderAgent` | `agents/rss_reader.py` | Fetches RSS feed, returns `list[NewsItem]` |
| `CuratorAgent` | `agents/curator.py` | Deduplicates by normalized headline text, trims to `max_items` |
| `SentimentAgent` | `agents/sentiment.py` | Runs VADER on each headline, returns a single `SentimentResult` for the category |
| `ReportWriterAgent` | `agents/report_writer.py` | Calls OpenAI with structured output schema, returns report dict |
| `ExecutiveSummaryAgent` | `agents/executive_summary.py` | Generates a top-level summary across all categories |
| `FutureOutlookAgent` | `agents/future_outlook.py` | Generates time-horizon forecasts |
| `PublisherAgent` | `agents/publisher.py` | Writes `YYYY-MM-DD.json` and updates `reports_index.json` |

### Core Data Models (`agents/base.py`)

```python
@dataclass
class NewsItem:
    title: str
    url: str
    published: Optional[str] = None
    summary: Optional[str] = None
    source: Optional[str] = None

@dataclass
class SentimentResult:
    score: float   # -1.0 to 1.0
    label: str     # "Positive" | "Neutral" | "Negative" | "Mixed"
    rationale: str
```

### Output JSON Schema (per category in `YYYY-MM-DD.json`)

```json
{
  "key": "technology",
  "title": "Technology",
  "source": { "site_name": "...", "site_url": "...", "feed_url": "..." },
  "sentiment": { "score": 0.12, "label": "Neutral", "rationale": "..." },
  "items": [{ "title": "...", "url": "...", "published": "...", "summary": "...", "source": "..." }],
  "ai_report": {
    "summary": "...",
    "key_themes": ["..."],
    "notable_headlines": [{ "headline": "...", "why_it_matters": "...", "signal": "Opportunity|Risk|Unclear" }],
    "future_outlook": {
      "next_24_72_hours": ["..."],
      "next_1_4_weeks": ["..."],
      "watch_list": ["..."],
      "confidence": "Low|Medium|High"
    },
    "caveats": ["..."]
  }
}
```

---

## News Sources (`pipeline/config.py`)

Defined as a frozen `CATEGORIES` dict of `CategoryConfig` dataclasses. Each category has exactly 12 items max (`max_items=12`).

| Key | Title | Source | Feed |
|---|---|---|---|
| `world` | World | BBC News | `feeds.bbci.co.uk/news/world/rss.xml` |
| `business` | Business | The Guardian | `theguardian.com/business/rss` |
| `technology` | Technology | The Verge | `theverge.com/rss/index.xml` |
| `sports` | Sports | ESPN | `espn.com/espn/rss/news` |
| `science` | Science | ScienceDaily | `sciencedaily.com/rss/top/science.xml` |

To add a new category: add a new `CategoryConfig` entry to `CATEGORIES` in `config.py`. The pipeline and frontend will pick it up automatically via the category key.

---

## OpenAI Integration

- **Default model:** `gpt-4o-mini`
- **Fallback chain:** `gpt-4o-mini` → `gpt-4o`
- **Pattern:** Structured Outputs (strict JSON schema validation)
- **Wrapper:** `agents/openai_compat.py` provides a unified interface; prefer using it over calling `openai` directly

Environment variable `OPENAI_MODEL` overrides the default. In GitHub Actions, it is read from the `OPENAI_MODEL` secret (optional).

---

## Graceful Degradation

The pipeline is designed to never crash the workflow:

1. **RSS failure** — if a feed cannot be fetched, the pipeline falls back to headlines from the most recent saved JSON report for that category.
2. **OpenAI failure** — `ReportWriterAgent` has internal retry/fallback logic. If it still fails, `run_daily.py` catches the exception and substitutes a stub report dict with `"confidence": "Low"`.
3. **No API key (local)** — pipeline runs in deterministic mode; `client = None` is passed to agents that skip the OpenAI call.

---

## Frontend (`news/`)

The frontend is plain HTML + CSS + JavaScript with **no build step and no npm**.

- **`app.js`** handles all interactivity: async JSON loading, date selector, tab switching, search/filter, dark/light mode toggle (persisted in `localStorage`), and a "broken grid" layout toggle.
- **`style.css`** uses a "brutal" minimalist aesthetic: dark background (`#0b0c10`), blue accent (`#25b7ff`), CSS Grid, glass-morphism borders, and animated ambient background blobs.
- Data is fetched from `news/data/reports_index.json` (index) and `news/data/reports/YYYY-MM-DD.json` (daily reports). A `_ts` cache-busting query parameter is appended to JSON requests.

Do not introduce JavaScript frameworks or a build system. Keep all frontend changes in the three files: `reports.html`, `app.js`, `style.css`.

---

## CI/CD Workflow (`.github/workflows/daily_news_reports.yml`)

| Property | Value |
|---|---|
| Schedule | Daily at 14:10 UTC (07:10 AM America/Denver) |
| Manual trigger | `workflow_dispatch` |
| Runner | `ubuntu-latest` |
| Python version | 3.11 |
| Working directory | `ai_news_reports_site` |
| Required secret | `OPENAI_API_KEY` |
| Optional secret | `OPENAI_MODEL` |
| Pages source | `ai_news_reports_site/` directory |

**Workflow steps:**
1. Checkout repository
2. Setup Python 3.11
3. `pip install -r requirements.txt`
4. `python -m pipeline.run_daily`
5. `git add ai_news_reports_site/news/data` + commit with message `Daily news report: YYYY-MM-DD [skip ci]` (only if changed)
6. Upload `ai_news_reports_site/` as Pages artifact
7. Deploy to GitHub Pages

The `[skip ci]` tag on auto-commits prevents infinite workflow loops.

---

## Key Conventions

- **Run the pipeline as a module:** `python -m pipeline.run_daily` (not `python pipeline/run_daily.py`) so relative imports resolve correctly.
- **Timezone:** The pipeline keys daily reports to `America/Denver` local date, not UTC.
- **No test framework:** There are no pytest tests. Correctness is validated through the pipeline's own fallback mechanisms and structured output schemas. When adding new logic, manually run the pipeline to verify.
- **Sentinel values:** Missing/inapplicable sentiment scores are stored as `"—"` (em-dash) in the JSON, not `null` or `0`.
- **Commit style:** `Update <filename>` for manual code changes; `Daily news report: YYYY-MM-DD [skip ci]` for automated report commits.
- **No `.env` files:** Environment variables are set in the shell locally or via GitHub Secrets in CI.
- **No Docker, no Makefile.** The setup is intentionally minimal.
- **`CATEGORIES` order matters:** The frontend renders tabs in the same order the keys appear in `CATEGORIES`.
- **Report index retention:** `PublisherAgent` keeps up to 45 months of report dates in `reports_index.json`.

---

## Adding or Changing Things

### Add a new news category
1. Add a `CategoryConfig` entry to `CATEGORIES` in `pipeline/config.py`.
2. The pipeline will automatically include it in the next run.
3. The frontend tab list is driven by the report JSON, so no frontend changes are needed.

### Change the AI model
- Locally: `export OPENAI_MODEL="gpt-4.1"`
- In CI: update the `OPENAI_MODEL` GitHub Secret.

### Change the report schedule
- Edit the `cron` expression in `.github/workflows/daily_news_reports.yml`. Times are UTC.

### Modify the AI report structure
- Update the JSON schema in `agents/report_writer.py`.
- Update `app.js` to render the new fields.
- Existing stored JSON files will not have the new fields — handle missing fields defensively in `app.js`.

### Modify the frontend design
- Edit `news/style.css` for styling.
- Edit `news/app.js` for behavior.
- Edit `news/reports.html` for markup.
- No build step needed; changes are live immediately on the next page load.
