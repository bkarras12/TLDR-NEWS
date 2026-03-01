# Agentic AI News Reports (Static Website + Daily GitHub Action)

This repo generates a **daily AI-written news report** and publishes it as a **static website** (GitHub Pages friendly).

## What you get

- `news/reports.html` — a clean UI with **5 tabs**:
  - World (BBC)
  - Business (The Guardian)
  - Technology (The Verge)
  - Sports (ESPN)
  - Science (ScienceDaily)
- `pipeline/run_daily.py` — the agent pipeline that:
  - reads RSS feeds (5 different news websites)
  - curates headlines
  - runs sentiment analysis
  - uses OpenAI to write a comprehensive report + future outlook
  - writes JSON files consumed by the website
- `.github/workflows/daily_news_reports.yml` — runs daily via cron and on manual dispatch.

## Setup (local)

1) Create a virtualenv + install dependencies
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
```

2) Set your OpenAI API key
```bash
# macOS/Linux
export OPENAI_API_KEY="YOUR_KEY"
# Windows PowerShell
$env:OPENAI_API_KEY="YOUR_KEY"
```

Optional:
```bash
export OPENAI_MODEL="gpt-4.1"
```

3) Run the pipeline
```bash
python pipeline/run_daily.py
```

Then open:
- `news/reports.html` (served from GitHub Pages, or via any static server)

## Setup (GitHub Pages)

1) Push this repo to GitHub
2) In **Settings → Secrets and variables → Actions**, add:
- `OPENAI_API_KEY`
- (optional) `OPENAI_MODEL`

3) In **Settings → Pages**, choose:
- **Source:** GitHub Actions (recommended)

4) The workflow will run daily and publish updated reports.

## Notes

- This project only uses RSS headlines + summaries. It does not scrape full articles.
- The website reads from JSON under `news/data/`.
