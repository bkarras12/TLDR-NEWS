# TL;DR News — Daily AI News Intelligence

An automated news aggregation system that publishes AI-generated daily news summaries as a static website. A GitHub Actions workflow runs every morning, pulls headlines from 5 major news sources via RSS, generates structured AI analysis using OpenAI, and deploys everything to GitHub Pages — zero human involvement required.

## What It Does

Every day at 7:10 AM Mountain Time, the pipeline:

1. **Fetches headlines** from 5 RSS feeds (BBC, The Guardian, The Verge, ESPN, ScienceDaily)
2. **Deduplicates and curates** the top 12 headlines per category
3. **Analyzes sentiment** using lexicon-based scoring (VADER)
4. **Generates AI reports** via OpenAI with structured output — including a key takeaway, executive summary, key themes, notable headlines with "why it matters" analysis, a forward-looking outlook, and caveats
5. **Publishes** JSON data, static HTML pages, RSS feeds, and a sitemap

The result is a fully self-updating news intelligence dashboard covering:

| Category | Source | Feed |
|---|---|---|
| World | BBC News | `feeds.bbci.co.uk/news/world/rss.xml` |
| Business | The Guardian | `theguardian.com/business/rss` |
| Technology | The Verge | `theverge.com/rss/index.xml` |
| Sports | ESPN | `espn.com/espn/rss/news` |
| Science | ScienceDaily | `sciencedaily.com/rss/top/science.xml` |

## How the Pipeline Works

The pipeline is a sequential chain of single-responsibility agents. Each agent has a `run()` method and handles one step:

```
RSS feeds → RssReaderAgent → CuratorAgent → SentimentAgent → ReportWriterAgent → PublisherAgent
```

**RssReaderAgent** — Fetches and parses RSS feeds using `feedparser`. Extracts title, link, published date, and summary from each entry.

**CuratorAgent** — Removes duplicate headlines by normalizing text (lowercasing, collapsing whitespace, trimming to 120 characters). Caps each category at 12 items.

**SentimentAgent** — Runs VADER sentiment analysis across all headlines and summaries for a category. Produces a single compound score (-1 to +1) with a label: Positive, Negative, Neutral, or Mixed.

**ReportWriterAgent** — Sends the curated headlines to OpenAI with a structured output schema. The AI returns:
- **Key takeaway** — one quotable sentence summarizing the day
- **Executive summary** — 2-4 sentence overview
- **Key themes** — 3-8 recurring topics
- **Notable headlines** — 5-10 items with "why it matters" analysis and a signal tag (Opportunity / Risk / Unclear)
- **Future outlook** — short-term forecasts (24-72 hours, 1-4 weeks) plus a watch list
- **Caveats** — limitations and disclaimers

If OpenAI fails, the agent falls back to a deterministic local report built from the headlines themselves.

**PublisherAgent** — Writes the daily JSON report, generates static HTML pages per category (with Schema.org structured data), creates RSS feeds, updates the sitemap, and maintains the reports index.

## What Gets Published

Each pipeline run produces:

```
news/
├── data/
│   ├── reports_index.json          # Index of all available dates
│   └── reports/
│       └── 2026-03-07.json         # Full daily report (~57 KB)
├── 2026-03-07/                     # Static HTML pages (one per category)
│   ├── index.html                  # Date overview page
│   ├── world.html
│   ├── business.html
│   ├── technology.html
│   ├── sports.html
│   └── science.html
├── world/index.html                # Category landing pages (always latest)
├── business/index.html
├── technology/index.html
├── sports/index.html
├── science/index.html
├── feeds/
│   ├── all.xml                     # Combined RSS feed
│   ├── world.xml                   # Per-category RSS feeds
│   ├── business.xml
│   ├── technology.xml
│   ├── sports.xml
│   └── science.xml
├── sitemap.xml                     # Auto-generated sitemap
├── robots.txt                      # Welcomes AI crawlers
├── reports.html                    # Main interactive dashboard
├── app.js                          # Frontend logic
└── style.css                       # Dashboard styling
```

The **static HTML pages** contain the full AI analysis baked directly into the markup with Schema.org `NewsArticle` and `FAQPage` structured data. These are designed for search engines and AI crawlers that don't execute JavaScript.

The **interactive dashboard** (`reports.html`) loads JSON dynamically and provides category tabs, date switching, headline search, dark/light mode, and a responsive mobile layout.

## Graceful Degradation

The pipeline is designed to never crash the workflow:

- **RSS failure** — falls back to headlines from the most recent saved report
- **OpenAI failure** — `ReportWriterAgent` retries with fallback models (gpt-4o-mini → gpt-4o), then generates a deterministic local report
- **No API key** — pipeline runs in deterministic mode; all reports are built from headlines without AI generation

## Local Setup

All commands run from inside `ai_news_reports_site/`:

```bash
cd ai_news_reports_site

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Set your API key
export OPENAI_API_KEY="sk-..."

# Optional: override the default model (gpt-4o-mini)
export OPENAI_MODEL="gpt-4o"

# Run the pipeline
python -m pipeline.run_daily
```

To view the site locally:

```bash
python -m http.server 8080 --directory ai_news_reports_site
# Open http://localhost:8080/news/reports.html
```

## GitHub Pages Deployment

1. Push the repo to GitHub
2. Go to **Settings → Secrets and variables → Actions** and add:
   - `OPENAI_API_KEY` (required)
   - `OPENAI_MODEL` (optional, defaults to `gpt-4o-mini`)
3. Go to **Settings → Pages** and set source to **GitHub Actions**
4. The workflow runs daily at 14:10 UTC and on manual dispatch

## Tech Stack

| Layer | Technology |
|---|---|
| Pipeline | Python 3.11 |
| AI | OpenAI API (structured outputs) |
| RSS parsing | feedparser |
| Sentiment | vaderSentiment (VADER lexicon) |
| Frontend | Vanilla JS, HTML5, CSS3 — no frameworks, no build step |
| Hosting | GitHub Pages (static) |
| CI/CD | GitHub Actions |

## Adding a New News Category

Add a `CategoryConfig` entry to `CATEGORIES` in `pipeline/config.py`:

```python
"health": CategoryConfig(
    key="health",
    title="Health",
    site_name="Medical News Today",
    site_url="https://www.medicalnewstoday.com",
    feed_url="https://rss.medicalnewstoday.com/featurednews.xml",
    max_items=12,
),
```

The pipeline and frontend pick it up automatically on the next run — no other changes needed.

## Notes

- This project only uses RSS headlines and summaries. It does not scrape full articles.
- Reports are keyed to America/Denver local date, not UTC.
- The pipeline must be run as a module: `python -m pipeline.run_daily` (not `python pipeline/run_daily.py`).
- The reports index retains up to 45 months of history.
- Missing sentiment scores are stored as `"—"` (em-dash), not `null`.
