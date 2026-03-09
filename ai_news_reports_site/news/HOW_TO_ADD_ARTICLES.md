# How to Add Articles

## 1. Create the markdown file

Add a new `.md` file to `news/articles/` with YAML frontmatter:

```
news/articles/<slug>.md
```

Example file `news/articles/2026-03-08-ai-reshaping-trade.md`:

```markdown
---
title: "Why AI Is Reshaping Global Trade"
date: 2026-03-08
author: Brady
category: technology
---

Your article content here. Supports **bold**, *italic*, lists, blockquotes, code blocks, images, etc.
```

### Frontmatter fields

| Field | Required | Description |
|---|---|---|
| `title` | Yes | Article title (shown on card and article page) |
| `date` | Yes | Publish date in `YYYY-MM-DD` format |
| `author` | Yes | Author name |
| `category` | Yes | One of: `world`, `business`, `technology`, `sports`, `science` |

## 2. Add it to the index

Edit `news/articles/articles_index.json` and add an entry:

```json
[
  {
    "slug": "2026-03-08-ai-reshaping-trade",
    "title": "Why AI Is Reshaping Global Trade",
    "date": "2026-03-08",
    "author": "Brady",
    "category": "technology"
  }
]
```

The `slug` must match the filename without the `.md` extension.

## 3. Commit and push

```bash
git add ai_news_reports_site/news/articles/
git commit -m "Add article: Why AI Is Reshaping Global Trade"
git push
```

The site deploys automatically on push.
