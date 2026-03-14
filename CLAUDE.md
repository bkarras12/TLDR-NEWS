# CLAUDE.md — TLDR-NEWS

Automated daily news aggregation system. GitHub Actions fetches RSS headlines from 5 sources, generates AI reports via OpenAI, and deploys a static site to GitHub Pages. No server, no database, no build step — pipeline writes JSON that vanilla JS reads client-side.

## Repository Layout

- `ai_news_reports_site/` — everything served on GitHub Pages
  - `pipeline/` — Python backend (entry point: `python -m pipeline.run_daily` from `ai_news_reports_site/`)
    - `config.py` — `CATEGORIES` dict of `CategoryConfig` dataclasses (5 sources, `max_items=12` each)
    - `run_daily.py` — orchestrates the agent chain
    - `agents/` — single-responsibility classes with `run()` methods
  - `news/` — static frontend (`reports.html`, `app.js`, `style.css`, `data/`)
  - `requirements.txt` — Python 3.11 deps: `openai`, `feedparser`, `vaderSentiment`, `requests`, `python-dateutil`, `tweepy`
- `.github/workflows/daily_news_reports.yml` — CI/CD

## Pipeline Agent Chain

```
RSS feeds → RssReaderAgent → CuratorAgent → SentimentAgent → ReportWriterAgent → PublisherAgent
```

| Agent | File | Role |
|---|---|---|
| `RssReaderAgent` | `rss_reader.py` | Fetches RSS feed → `list[NewsItem]` |
| `CuratorAgent` | `curator.py` | Deduplicates headlines, trims to `max_items` |
| `SentimentAgent` | `sentiment.py` | VADER sentiment → `SentimentResult` per category |
| `ReportWriterAgent` | `report_writer.py` | OpenAI structured output → report dict |
| `ExecutiveSummaryAgent` | `executive_summary.py` | Cross-category summary |
| `FutureOutlookAgent` | `future_outlook.py` | Time-horizon forecasts |
| `TweetWriterAgent` | `tweet_writer.py` | Generates tweet content |
| `ArticleWriterAgent` | `article_writer.py` | Generates article content |
| `ReplyWriterAgent` | `reply_writer.py` | Generates reply content |
| `PublisherAgent` | `publisher.py` | Writes `YYYY-MM-DD.json`, updates `reports_index.json` (retains last 45 entries) |

Utility: `openai_compat.py` — unified OpenAI wrapper with fallback chain (Structured Outputs → JSON mode → text).

## News Sources (`config.py`)

| Key | Source | Feed |
|---|---|---|
| `world` | BBC News | `feeds.bbci.co.uk/news/world/rss.xml` |
| `business` | The Guardian | `theguardian.com/business/rss` |
| `technology` | The Verge | `theverge.com/rss/index.xml` |
| `sports` | ESPN | `espn.com/espn/rss/news` |
| `science` | ScienceDaily | `sciencedaily.com/rss/top/science.xml` |

`CATEGORIES` order matters — frontend renders tabs in this order. To add a category, add a `CategoryConfig` entry; pipeline and frontend pick it up automatically.

## OpenAI Integration

- **Default model:** `gpt-4o-mini` — **Fallback:** `gpt-4o`
- **Override:** `OPENAI_MODEL` env var (locally) or GitHub Secret (CI)
- **Wrapper:** always use `openai_compat.py` over raw `openai` calls
- **No API key:** pipeline runs in deterministic stub mode (`client = None`)

## Report JSON Schema (`news/data/reports/YYYY-MM-DD.json`)

Each category object contains: `key`, `title`, `source`, `sentiment` (`score`/`label`/`rationale`), `items` (list of `NewsItem`), and `ai_report` with fields: `key_takeaway`, `summary`, `key_themes`, `notable_headlines` (each with `headline`/`why_it_matters`/`signal`), `future_outlook` (`next_24_72_hours`/`next_1_4_weeks`/`watch_list`/`confidence`), `caveats`, `related_topics`.

Signal enum: `Opportunity | Risk | Unclear`. Confidence enum: `Low | Medium | High`.

## Graceful Degradation

1. **RSS failure** — falls back to headlines from the most recent saved JSON for that category
2. **OpenAI failure** — retry/fallback logic in `ReportWriterAgent`; `run_daily.py` substitutes a stub report on exception
3. **No API key** — deterministic mode, AI content absent

## Frontend (`news/`)

Vanilla HTML + CSS + JS. No frameworks, no build system, no npm.

- `app.js` — JSON loading, date selector, tab switching, search/filter, dark/light mode (persisted in `localStorage`)
- `style.css` — dark theme (`#0b0c10`), blue accent (`#25b7ff`), CSS Grid, glass-morphism, ambient blobs
- Data fetched with `_ts` cache-busting query parameter
- Keep all frontend changes in `reports.html`, `app.js`, `style.css`

## CI/CD Workflow

Runs **3x daily** (cron: `0 14 * * *`, `0 23 * * *`, `0 3 * * *` UTC) + manual `workflow_dispatch`.

Steps: checkout → Python 3.11 → pip install → `python -m pipeline.run_daily` → git commit data (`Daily news report: YYYY-MM-DD [skip ci]`) → deploy to GitHub Pages.

Required secret: `OPENAI_API_KEY`. Optional: `OPENAI_MODEL`.

## Local Development

```bash
cd ai_news_reports_site
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."   # optional — stub mode without it
python -m pipeline.run_daily
# Frontend: python -m http.server 8080 --directory . → http://localhost:8080/news/reports.html
```

## Key Conventions

- **Run as module:** `python -m pipeline.run_daily` (not `python pipeline/run_daily.py`)
- **Timezone:** reports keyed to `America/Denver` local date, not UTC
- **No tests:** validate by running the pipeline manually
- **Sentinel values:** missing sentiment scores stored as `"—"` (em-dash), not `null` or `0`
- **Commit style:** `Update <filename>` for code changes; `Daily news report: YYYY-MM-DD [skip ci]` for automated commits
- **No `.env`, no Docker, no Makefile** — minimal by design

## Modifying the Project

- **New category:** add `CategoryConfig` to `CATEGORIES` in `config.py`
- **Change model:** set `OPENAI_MODEL` env var or GitHub Secret
- **Change schedule:** edit cron in `.github/workflows/daily_news_reports.yml` (UTC)
- **Change report structure:** update schema in `report_writer.py` + render logic in `app.js`; handle missing fields defensively for older reports
