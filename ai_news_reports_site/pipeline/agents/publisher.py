from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class PublisherAgent:
    def __init__(self, site_root: Path):
        self.site_root = site_root
        self.reports_dir = self.site_root / "news" / "data" / "reports"
        self.index_path = self.site_root / "news" / "data" / "reports_index.json"

        self.reports_dir.mkdir(parents=True, exist_ok=True)
        (self.site_root / "news" / "data").mkdir(parents=True, exist_ok=True)

    def write_daily_report(self, date_key: str, report: Dict[str, Any]) -> Path:
        out_path = self.reports_dir / f"{date_key}.json"
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return out_path

    def update_index(self, date_key: str, available_categories: List[str], keep_last: int = 45) -> None:
        idx: Dict[str, Any] = {"latest_date": date_key, "dates": []}

        if self.index_path.exists():
            try:
                idx = json.loads(self.index_path.read_text(encoding="utf-8"))
            except Exception:
                idx = {"latest_date": date_key, "dates": []}

        # Remove existing entry for the same date (if rerun)
        idx_dates = [d for d in idx.get("dates", []) if d.get("date") != date_key]

        # Prepend new entry (newest on top)
        idx_dates.insert(0, {"date": date_key, "categories": available_categories})

        # Trim
        idx_dates = idx_dates[:keep_last]

        idx["latest_date"] = idx_dates[0]["date"] if idx_dates else date_key
        idx["dates"] = idx_dates

        self.index_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ── Static HTML pages (GEO) ─────────────────────────────

    def write_static_pages(self, date_key: str, report: Dict[str, Any]) -> List[Path]:
        """Generate one static HTML page per category for AI crawler consumption."""
        categories = report.get("categories") or {}
        model = report.get("model", "")
        pages_dir = self.site_root / "news" / date_key
        pages_dir.mkdir(parents=True, exist_ok=True)
        written: List[Path] = []

        for cat_key, cat in categories.items():
            page_path = pages_dir / f"{cat_key}.html"
            page_html = self._render_category_page(date_key, cat_key, cat, model)
            page_path.write_text(page_html, encoding="utf-8")
            written.append(page_path)

        # Date index page listing all categories for that day
        index_path = pages_dir / "index.html"
        index_path.write_text(
            self._render_date_index(date_key, categories, model), encoding="utf-8"
        )
        written.append(index_path)

        return written

    def write_category_landing_pages(self, date_key: str, report: Dict[str, Any]) -> List[Path]:
        """Generate /news/<category>/index.html landing pages showing the latest report."""
        categories = report.get("categories") or {}
        model = report.get("model", "")
        written: List[Path] = []

        for cat_key, cat in categories.items():
            cat_dir = self.site_root / "news" / cat_key
            cat_dir.mkdir(parents=True, exist_ok=True)
            page_path = cat_dir / "index.html"
            page_html = self._render_category_page(date_key, cat_key, cat, model, is_landing=True)
            page_path.write_text(page_html, encoding="utf-8")
            written.append(page_path)

        return written

    def write_sitemap(self, base_url: str = "") -> Path:
        """Generate sitemap.xml from the reports index."""
        idx = self._read_index()
        urls: List[str] = []

        # Main app page
        urls.append(self._sitemap_url(base_url, "news/reports.html"))

        for entry in idx.get("dates", []):
            date = entry.get("date", "")
            # Date index page
            urls.append(self._sitemap_url(base_url, f"news/{date}/index.html", lastmod=date))
            for cat in entry.get("categories", []):
                urls.append(self._sitemap_url(base_url, f"news/{date}/{cat}.html", lastmod=date))
                # Category landing pages (only for latest date)
                if date == idx.get("latest_date"):
                    urls.append(self._sitemap_url(base_url, f"news/{cat}/index.html", lastmod=date))

        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        xml += "\n".join(urls)
        xml += "\n</urlset>\n"

        sitemap_path = self.site_root / "news" / "sitemap.xml"
        sitemap_path.write_text(xml, encoding="utf-8")
        return sitemap_path

    def write_rss_feeds(self, date_key: str, report: Dict[str, Any], base_url: str = "") -> List[Path]:
        """Generate RSS feeds: one combined feed and one per category."""
        categories = report.get("categories") or {}
        feeds_dir = self.site_root / "news" / "feeds"
        feeds_dir.mkdir(parents=True, exist_ok=True)
        written: List[Path] = []

        # Combined feed
        all_items_xml: List[str] = []
        for cat_key, cat in categories.items():
            all_items_xml.extend(self._rss_items_for_category(date_key, cat_key, cat, base_url))

        combined_path = feeds_dir / "all.xml"
        combined_path.write_text(
            self._wrap_rss_feed(
                title="TL;DR News — Daily AI Intelligence",
                description="AI-generated daily news summaries across world, business, technology, sports, and science.",
                link=f"{base_url}news/reports.html",
                items=all_items_xml,
            ),
            encoding="utf-8",
        )
        written.append(combined_path)

        # Per-category feeds
        for cat_key, cat in categories.items():
            cat_title = cat.get("title", cat_key.title())
            cat_items = self._rss_items_for_category(date_key, cat_key, cat, base_url)
            cat_path = feeds_dir / f"{cat_key}.xml"
            cat_path.write_text(
                self._wrap_rss_feed(
                    title=f"TL;DR News — {cat_title}",
                    description=f"Daily AI-generated {cat_title.lower()} news summary.",
                    link=f"{base_url}news/{cat_key}/index.html",
                    items=cat_items,
                ),
                encoding="utf-8",
            )
            written.append(cat_path)

        return written

    # ── Private helpers ──────────────────────────────────────

    def _read_index(self) -> Dict[str, Any]:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"latest_date": None, "dates": []}

    @staticmethod
    def _e(text: Any) -> str:
        """HTML-escape a value."""
        return html.escape(str(text or ""), quote=True)

    @staticmethod
    def _ex(text: Any) -> str:
        """XML-escape a value for RSS/sitemap."""
        s = str(text or "")
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

    @staticmethod
    def _sitemap_url(base: str, path: str, lastmod: Optional[str] = None) -> str:
        loc = f"{base}{path}" if base else path
        parts = [f"  <url>\n    <loc>{loc}</loc>"]
        if lastmod:
            parts.append(f"    <lastmod>{lastmod}</lastmod>")
        parts.append("  </url>")
        return "\n".join(parts)

    def _render_category_page(
        self, date_key: str, cat_key: str, cat: Dict[str, Any], model: str, is_landing: bool = False
    ) -> str:
        e = self._e
        title = cat.get("title", cat_key.title())
        src = cat.get("source") or {}
        sent = cat.get("sentiment") or {}
        rep = cat.get("ai_report") or {}
        items = cat.get("items") or []

        key_takeaway = rep.get("key_takeaway", "")
        summary = rep.get("summary", "")
        key_themes = rep.get("key_themes") or []
        notable = rep.get("notable_headlines") or []
        outlook = rep.get("future_outlook") or {}
        caveats = rep.get("caveats") or []

        page_title = f"{title} News Summary — {date_key}"
        meta_desc = key_takeaway or summary[:160]

        # Schema.org JSON-LD
        schema_ld = json.dumps({
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": f"{title} News Summary — {date_key}",
            "datePublished": date_key,
            "dateModified": date_key,
            "description": meta_desc,
            "articleSection": title,
            "author": {
                "@type": "Organization",
                "name": "TL;DR News AI",
            },
            "publisher": {
                "@type": "Organization",
                "name": "TL;DR News",
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
            },
            "about": key_themes[:5],
        }, ensure_ascii=False, indent=2)

        # FAQ Schema for notable headlines
        faq_items = []
        for n in notable[:10]:
            headline = n.get("headline", "")
            why = n.get("why_it_matters", "")
            if headline and why:
                faq_items.append({
                    "@type": "Question",
                    "name": f"Why does \"{headline}\" matter?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": why,
                    },
                })

        faq_ld = ""
        if faq_items:
            faq_ld = json.dumps({
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": faq_items,
            }, ensure_ascii=False, indent=2)

        # Build headline items HTML
        items_html = ""
        for it in items:
            it_title = e(it.get("title", ""))
            it_url = e(it.get("url", "#"))
            it_pub = e(it.get("published", ""))
            it_src = e(it.get("source", ""))
            it_sum = e(it.get("summary", ""))
            items_html += f"""      <article class="headline-item">
        <h3><a href="{it_url}" rel="noopener">{it_title}</a></h3>
        <p class="meta">Published: {it_pub} — via {it_src}</p>
        {f'<p>{it_sum}</p>' if it_sum else ''}
      </article>
"""

        # Notable headlines as FAQ
        faq_html = ""
        for n in notable:
            headline = e(n.get("headline", ""))
            why = e(n.get("why_it_matters", ""))
            signal = e(n.get("signal", "Unclear"))
            if headline and why:
                faq_html += f"""      <details>
        <summary><strong>Why does &quot;{headline}&quot; matter?</strong> <span class="signal">[{signal}]</span></summary>
        <p>{why}</p>
      </details>
"""

        # Outlook
        out_72 = outlook.get("next_24_72_hours") or []
        out_4w = outlook.get("next_1_4_weeks") or []
        watchlist = outlook.get("watch_list") or []
        confidence = outlook.get("confidence", "—")

        landing_note = ""
        if is_landing:
            landing_note = f'    <p><em>This is the latest {e(title)} report. <a href="../{date_key}/{cat_key}.html">Permalink for {date_key}</a>.</em></p>\n'

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{e(page_title)}</title>
  <meta name="description" content="{e(meta_desc)}">
  <meta name="robots" content="index, follow, max-snippet:-1">
  <link rel="canonical" href="{date_key}/{cat_key}.html">
  <link rel="alternate" type="application/rss+xml" title="TL;DR News — {e(title)}" href="../feeds/{cat_key}.xml">
  <link rel="alternate" type="application/rss+xml" title="TL;DR News — All Categories" href="../feeds/all.xml">
  <script type="application/ld+json">
{schema_ld}
  </script>
{f'''  <script type="application/ld+json">
{faq_ld}
  </script>''' if faq_ld else ''}
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; color: #1a1a2e; background: #fafbff; }}
    h1 {{ font-size: 1.6em; border-bottom: 2px solid #0099bb; padding-bottom: 8px; }}
    h2 {{ font-size: 1.2em; color: #0099bb; margin-top: 1.5em; }}
    .key-takeaway {{ font-size: 1.15em; font-weight: 600; padding: 14px 18px; background: #e8f7fa; border-left: 4px solid #0099bb; margin: 16px 0; }}
    .themes {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }}
    .theme {{ padding: 4px 10px; border-radius: 999px; background: #e8f7fa; font-size: 0.85em; }}
    .signal {{ font-size: 0.85em; color: #666; }}
    details {{ margin: 8px 0; padding: 8px 12px; border: 1px solid #e0e0e0; border-radius: 6px; }}
    details summary {{ cursor: pointer; }}
    .headline-item {{ padding: 10px 0; border-bottom: 1px solid #eee; }}
    .headline-item h3 {{ margin: 0 0 4px; font-size: 1em; }}
    .headline-item .meta {{ font-size: 0.8em; color: #888; margin: 0; }}
    .headline-item p {{ margin: 4px 0 0; font-size: 0.9em; }}
    a {{ color: #0099bb; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .outlook-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin: 10px 0; }}
    .outlook-card {{ padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; background: #f8f9fc; }}
    .outlook-card h3 {{ margin: 0 0 8px; font-size: 0.95em; }}
    .outlook-card ul {{ margin: 0; padding-left: 18px; }}
    .outlook-card li {{ font-size: 0.9em; margin-bottom: 4px; }}
    nav {{ font-size: 0.9em; margin-bottom: 16px; }}
    nav a {{ margin-right: 12px; }}
    footer {{ margin-top: 30px; padding-top: 14px; border-top: 1px solid #e0e0e0; font-size: 0.8em; color: #888; }}
  </style>
</head>
<body>
  <nav aria-label="Site navigation">
    <a href="../reports.html">Dashboard</a>
    <a href="../{date_key}/index.html">{date_key} Report</a>
    <a href="../feeds/{cat_key}.xml">RSS Feed</a>
  </nav>

  <article>
    <h1>{e(title)} News Summary — {e(date_key)}</h1>
{landing_note}
    <p>Source: <a href="{e(src.get('site_url', ''))}" rel="noopener">{e(src.get('site_name', ''))}</a>
      | Sentiment: <strong>{e(sent.get('label', '—'))}</strong> ({e(sent.get('score', '—'))})
      | Confidence: <strong>{e(confidence)}</strong>
    </p>

{f'    <div class="key-takeaway">{e(key_takeaway)}</div>' if key_takeaway else ''}

    <h2>Executive Summary</h2>
    <p>{e(summary)}</p>

    <h2>Key Themes</h2>
    <div class="themes">
{''.join(f'      <span class="theme">{e(t)}</span>' + chr(10) for t in key_themes)}
    </div>

    <h2>Why These Headlines Matter</h2>
{faq_html}

    <h2>Future Outlook</h2>
    <div class="outlook-grid">
      <div class="outlook-card">
        <h3>Next 24–72 Hours</h3>
        <ul>{''.join(f'<li>{e(x)}</li>' for x in out_72)}</ul>
      </div>
      <div class="outlook-card">
        <h3>Next 1–4 Weeks</h3>
        <ul>{''.join(f'<li>{e(x)}</li>' for x in out_4w)}</ul>
      </div>
      <div class="outlook-card">
        <h3>Watch List</h3>
        <ul>{''.join(f'<li>{e(x)}</li>' for x in watchlist)}</ul>
      </div>
    </div>

    <h2>Caveats</h2>
    <ul>
{''.join(f'      <li>{e(c)}</li>' + chr(10) for c in caveats)}
    </ul>

    <h2>All Headlines</h2>
{items_html}
  </article>

  <footer>
    <p>Generated by TL;DR News AI{f' using {e(model)}' if model else ''} on {e(date_key)}. Daily AI-powered news intelligence.</p>
  </footer>
</body>
</html>
"""

    def _render_date_index(self, date_key: str, categories: Dict[str, Any], model: str) -> str:
        e = self._e
        links = ""
        for cat_key, cat in categories.items():
            title = cat.get("title", cat_key.title())
            takeaway = (cat.get("ai_report") or {}).get("key_takeaway", "")
            links += f'    <li><a href="{cat_key}.html"><strong>{e(title)}</strong></a>'
            if takeaway:
                links += f" — {e(takeaway)}"
            links += "</li>\n"

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Daily News Summary — {e(date_key)} — TL;DR News</title>
  <meta name="description" content="AI-generated news summaries for {e(date_key)} across world, business, technology, sports, and science.">
  <meta name="robots" content="index, follow">
  <link rel="alternate" type="application/rss+xml" title="TL;DR News" href="../feeds/all.xml">
  <script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  "name": "Daily News Summary — {e(date_key)}",
  "datePublished": "{e(date_key)}",
  "description": "AI-generated news summaries for {e(date_key)}",
  "publisher": {{ "@type": "Organization", "name": "TL;DR News" }}
}}
  </script>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px; line-height: 1.6; color: #1a1a2e; background: #fafbff; }}
    h1 {{ font-size: 1.5em; border-bottom: 2px solid #0099bb; padding-bottom: 8px; }}
    a {{ color: #0099bb; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    li {{ margin-bottom: 10px; }}
    nav {{ font-size: 0.9em; margin-bottom: 16px; }}
    footer {{ margin-top: 30px; padding-top: 14px; border-top: 1px solid #e0e0e0; font-size: 0.8em; color: #888; }}
  </style>
</head>
<body>
  <nav><a href="../reports.html">Dashboard</a> | <a href="../feeds/all.xml">RSS Feed</a></nav>
  <h1>News Summary — {e(date_key)}</h1>
  <p>AI-generated daily news intelligence across 5 categories.</p>
  <ul>
{links}  </ul>
  <footer>
    <p>Generated by TL;DR News AI{f' using {e(model)}' if model else ''} on {e(date_key)}.</p>
  </footer>
</body>
</html>
"""

    def _rss_items_for_category(self, date_key: str, cat_key: str, cat: Dict[str, Any], base_url: str) -> List[str]:
        ex = self._ex
        title = cat.get("title", cat_key.title())
        rep = cat.get("ai_report") or {}
        key_takeaway = rep.get("key_takeaway", "")
        summary = rep.get("summary", "")

        description = key_takeaway or summary
        link = f"{base_url}news/{date_key}/{cat_key}.html"

        # RFC 822 date for RSS
        try:
            dt = datetime.strptime(date_key, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        except ValueError:
            pub_date = date_key

        items: List[str] = []
        items.append(f"""    <item>
      <title>{ex(title)} News Summary — {ex(date_key)}</title>
      <link>{ex(link)}</link>
      <description>{ex(description)}</description>
      <pubDate>{ex(pub_date)}</pubDate>
      <guid isPermaLink="true">{ex(link)}</guid>
      <category>{ex(title)}</category>
    </item>""")
        return items

    @staticmethod
    def _wrap_rss_feed(title: str, description: str, link: str, items: List[str]) -> str:
        now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        items_str = "\n".join(items)
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{title}</title>
    <link>{link}</link>
    <description>{description}</description>
    <language>en-us</language>
    <lastBuildDate>{now}</lastBuildDate>
    <generator>TL;DR News AI Pipeline</generator>
{items_str}
  </channel>
</rss>
"""
