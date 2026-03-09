# TLDR-NEWS: Resume & LinkedIn Entries

Use whichever version fits your situation. Customize the metrics and role title as needed.

---

## Resume Version (3-5 Bullet Points)

**TLDR-NEWS — Automated AI News Intelligence Platform** | Python, OpenAI API, JavaScript, GitHub Actions
*Personal Project — [github.com/your-handle/TLDR-NEWS](https://github.com/your-handle/TLDR-NEWS)*

- Engineered a fully automated news intelligence pipeline in Python that aggregates 60+ headlines daily from 5 RSS sources (BBC, The Guardian, ESPN, The Verge, ScienceDaily), applies VADER sentiment analysis, and generates structured AI reports via OpenAI's Structured Outputs API — deployed as a zero-dependency static site on GitHub Pages
- Architected a 7-agent processing chain (RSS reader, deduplicator, sentiment analyzer, report writer, executive summary, future outlook, publisher) with multi-level graceful degradation ensuring 100% pipeline uptime even during API outages or feed failures
- Built an 800+ line vanilla JavaScript dashboard featuring real-time category filtering, SVG sentiment trend visualization, dark/light theming with localStorage persistence, and cache-busted async data loading — all without frameworks or build tools
- Automated the full CI/CD lifecycle via GitHub Actions (scheduled 3x daily), generating 40+ SEO-optimized static HTML pages per run with Schema.org JSON-LD, OpenGraph meta tags, dynamic RSS feeds, and XML sitemaps
- Implemented intelligent cross-category trending topic detection using keyword extraction with 97+ stop-word filtering, identifying topics appearing across 2+ news categories to surface emerging stories

---

## Resume Version — Condensed (For Limited Space)

**TLDR-NEWS — AI News Intelligence Platform** | Python, OpenAI API, Vanilla JS, GitHub Actions

- Built an automated pipeline processing 60+ daily headlines from 5 RSS sources through a 7-agent chain (ingestion, deduplication, sentiment analysis, AI report generation, static publishing) with multi-level fallback ensuring zero-downtime operation
- Developed a framework-free JavaScript dashboard with SVG charting, real-time filtering, and theme persistence; automated CI/CD generates 40+ SEO-optimized pages daily via GitHub Actions and deploys to GitHub Pages

---

## LinkedIn "Experience" or "Projects" Entry

### Title
**Creator & Solo Developer** — TLDR-NEWS

### Description

I built TLDR-NEWS to solve a personal frustration: keeping up with world news without spending hours scrolling. It's a fully automated system that runs every morning, reads 60+ headlines from 5 major news sources, and uses AI to generate structured daily briefings — no manual intervention required.

**What it does:**
The Python pipeline fetches RSS feeds from BBC News, The Guardian, The Verge, ESPN, and ScienceDaily, deduplicates headlines, runs sentiment analysis, then sends everything to OpenAI's Structured Outputs API to produce key themes, notable headlines with "why it matters" context, and forward-looking predictions. Results are published as a static site on GitHub Pages.

**How it's built:**
I designed a modular 7-agent architecture where each agent (RSS reader, curator, sentiment analyzer, report writer, executive summary generator, future outlook analyst, publisher) has a single responsibility and its own fallback behavior. If an RSS feed goes down, the system loads from its 45-month archive. If OpenAI is unreachable, it falls back through a model chain and ultimately generates a deterministic stub report. The pipeline has never missed a day.

The frontend is intentionally zero-dependency — 800+ lines of vanilla JavaScript powering async data loading, SVG sentiment trend charts, multi-tab navigation, search/filter, and dark/light theming. GitHub Actions handles scheduling (3x daily) and deploys 40+ static HTML pages with Schema.org structured data, OpenGraph tags, and auto-generated RSS feeds.

**Key technologies:** Python 3.11, OpenAI Structured Outputs, feedparser, VADER Sentiment, GitHub Actions, GitHub Pages, Vanilla JS/HTML5/CSS3

---

## LinkedIn "About" Section Snippet (If You Want to Reference It)

> ...I also built TLDR-NEWS, an automated AI news intelligence platform that processes 60+ headlines daily from 5 major sources through a multi-agent Python pipeline and publishes structured AI briefings to a static site — fully hands-off via GitHub Actions CI/CD.

---

## Key Phrases for ATS / Recruiter Search Matching

Use these keywords naturally in your profile to improve discoverability:

- Python, OpenAI API, LLM integration, structured outputs
- RSS, data pipeline, ETL, automation
- Sentiment analysis, NLP, VADER
- GitHub Actions, CI/CD, static site generation
- Vanilla JavaScript, HTML5, CSS3, SVG
- GitHub Pages, SEO, Schema.org, JSON-LD
- Graceful degradation, fault tolerance, resilience engineering
- Agent architecture, modular design, single responsibility

---

## Tips for Using These

1. **Tailor to the job**: If applying for a backend role, lead with the Python pipeline and agent architecture. For frontend roles, lead with the vanilla JS dashboard. For DevOps/platform roles, lead with the CI/CD and static generation pipeline.
2. **Add your own metrics**: If you have analytics (page views, users, days running without failure), add them. Recruiters love concrete numbers.
3. **Link to it**: Include the live site URL and GitHub repo in both your resume and LinkedIn. Recruiters click through to verify claims.
4. **Update the tech stack**: If you swap OpenAI for another provider or add new features, update these entries to reflect current state.
