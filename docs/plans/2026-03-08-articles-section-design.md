# Articles Section — Design

**Date:** 2026-03-08
**Status:** Approved

## Overview

Add a separate articles page to the website where manually written long-form markdown articles can be published alongside the automated daily reports.

## How It Works

Drop a markdown file with frontmatter into `news/articles/`, add an entry to `articles_index.json`, commit and push. The site deploys automatically via the existing push trigger.

## File Structure

```
news/
├── articles.html              # Articles listing page
├── articles.js                # Article listing + rendering logic
├── articles/
│   ├── articles_index.json    # Index of all articles
│   └── <slug>.md              # Individual articles
```

## Markdown Frontmatter Format

```markdown
---
title: "Why AI Is Reshaping Global Trade"
date: 2026-03-08
author: Brady
category: technology
---

Article content here...
```

## Article Index (`articles_index.json`)

```json
[
  {
    "slug": "2026-03-08-why-ai-reshaping-trade",
    "title": "Why AI Is Reshaping Global Trade",
    "date": "2026-03-08",
    "author": "Brady",
    "category": "technology"
  }
]
```

## Frontend

- `articles.html` uses the same sidebar/shell as `reports.html`
- Both sidebars get links to navigate between Reports and Articles
- Listing view shows article cards (title, date, author, category), sorted newest first
- Click an article to render full markdown via marked.js (CDN, ~7KB)
- Same dark/light brutal aesthetic as the rest of the site

## Files Created/Modified

| File | Action |
|---|---|
| `news/articles.html` | New — articles page |
| `news/articles.js` | New — article listing + rendering logic |
| `news/articles/articles_index.json` | New — empty article index |
| `news/reports.html` | Modified — add Articles link to sidebar |
| `news/style.css` | Modified — article-specific styles |
