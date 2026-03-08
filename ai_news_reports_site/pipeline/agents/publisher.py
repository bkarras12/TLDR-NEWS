from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any, Dict, List


class PublisherAgent:
    BASE_URL = "https://bkarras12.github.io/TLDR-NEWS/"

    def __init__(self, site_root: Path):
        self.site_root = site_root
        self.reports_dir = self.site_root / "news" / "data" / "reports"
        self.index_path = self.site_root / "news" / "data" / "reports_index.json"

        self.reports_dir.mkdir(parents=True, exist_ok=True)
        (self.site_root / "news" / "data").mkdir(parents=True, exist_ok=True)

    # ── helpers ──

    @staticmethod
    def _e(text: str) -> str:
        return html.escape(str(text), quote=True)

    def _read_index(self) -> Dict[str, Any]:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"latest_date": "", "dates": []}

    # ── JSON output ──

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

        idx_dates = [d for d in idx.get("dates", []) if d.get("date") != date_key]
        idx_dates.insert(0, {"date": date_key, "categories": available_categories})
        idx_dates = idx_dates[:keep_last]

        idx["latest_date"] = idx_dates[0]["date"] if idx_dates else date_key
        idx["dates"] = idx_dates

        self.index_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ── Static HTML pages ──

    def write_static_pages(self, date_key: str, daily_report: Dict[str, Any]) -> List[Path]:
        date_dir = self.site_root / "news" / date_key
        date_dir.mkdir(parents=True, exist_ok=True)
        model = daily_report.get("model", "")
        cats = daily_report.get("categories", {})
        written: List[Path] = []

        # Date index page
        idx_path = date_dir / "index.html"
        idx_path.write_text(self._render_date_index(date_key, cats, model), encoding="utf-8")
        written.append(idx_path)

        # Per-category pages
        for cat_key, cat in cats.items():
            cat_path = date_dir / f"{cat_key}.html"
            cat_path.write_text(
                self._render_category_page(date_key, cat_key, cat, model),
                encoding="utf-8",
            )
            written.append(cat_path)

        return written

    def write_category_landing_pages(self, date_key: str, daily_report: Dict[str, Any]) -> List[Path]:
        cats = daily_report.get("categories", {})
        model = daily_report.get("model", "")
        written: List[Path] = []

        for cat_key, cat in cats.items():
            landing_dir = self.site_root / "news" / cat_key
            landing_dir.mkdir(parents=True, exist_ok=True)
            landing_path = landing_dir / "index.html"
            landing_path.write_text(
                self._render_category_page(date_key, cat_key, cat, model, is_landing=True),
                encoding="utf-8",
            )
            written.append(landing_path)

        return written

    # ── Sitemap ──

    def write_sitemap(self) -> Path:
        idx = self._read_index()
        e = self._e
        base = self.BASE_URL.rstrip("/")
        entries: List[str] = []

        entries.append(
            f"  <url><loc>{e(base)}/news/reports.html</loc>"
            f"<changefreq>daily</changefreq><priority>1.0</priority></url>"
        )

        for d_entry in idx.get("dates", []):
            d = d_entry.get("date", "")
            entries.append(
                f"  <url><loc>{e(base)}/news/{e(d)}/index.html</loc>"
                f"<lastmod>{e(d)}</lastmod><changefreq>monthly</changefreq><priority>0.7</priority></url>"
            )
            for cat_key in d_entry.get("categories", []):
                entries.append(
                    f"  <url><loc>{e(base)}/news/{e(d)}/{e(cat_key)}.html</loc>"
                    f"<lastmod>{e(d)}</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>"
                )

        for cat_key in (idx.get("dates", [{}])[0].get("categories", []) if idx.get("dates") else []):
            entries.append(
                f"  <url><loc>{e(base)}/news/{e(cat_key)}/index.html</loc>"
                f"<changefreq>daily</changefreq><priority>0.8</priority></url>"
            )

        content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(entries) + "\n"
            "</urlset>\n"
        )
        path = self.site_root / "news" / "sitemap.xml"
        path.write_text(content, encoding="utf-8")
        return path

    # ── RSS feeds ──

    def write_rss_feeds(self, date_key: str, daily_report: Dict[str, Any]) -> List[Path]:
        feeds_dir = self.site_root / "news" / "feeds"
        feeds_dir.mkdir(parents=True, exist_ok=True)
        base = self.BASE_URL.rstrip("/")
        cats = daily_report.get("categories", {})
        written: List[Path] = []

        all_items_xml: List[str] = []
        for cat_key, cat in cats.items():
            cat_items = self._rss_items_for_category(date_key, cat_key, cat, base)
            all_items_xml.extend(cat_items)

            # Per-category feed
            cat_title = cat.get("title", cat_key.title())
            cat_feed = self._wrap_rss_channel(
                title=f"TL;DR News — {cat_title}",
                link=f"{base}/news/{cat_key}/index.html",
                description=f"Daily AI-generated {cat_title.lower()} news summaries",
                items=cat_items,
            )
            cat_path = feeds_dir / f"{cat_key}.xml"
            cat_path.write_text(cat_feed, encoding="utf-8")
            written.append(cat_path)

        # Combined feed
        all_feed = self._wrap_rss_channel(
            title="TL;DR News — All Categories",
            link=f"{base}/news/reports.html",
            description="Daily AI-generated news summaries across all categories",
            items=all_items_xml,
        )
        all_path = feeds_dir / "all.xml"
        all_path.write_text(all_feed, encoding="utf-8")
        written.append(all_path)

        return written

    def _rss_items_for_category(self, date_key: str, cat_key: str, cat: Dict[str, Any], base_url: str) -> List[str]:
        e = self._e
        title = cat.get("title", cat_key.title())
        rep = cat.get("ai_report") or {}
        key_takeaway = rep.get("key_takeaway", "")
        summary = rep.get("summary", "")
        desc = key_takeaway or summary[:300]
        link = f"{base_url}/news/{date_key}/{cat_key}.html"

        try:
            pub_dt = datetime.strptime(date_key, "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc)
            pub_date = format_datetime(pub_dt)
        except Exception:
            pub_date = date_key

        return [
            f"    <item>\n"
            f"      <title>{e(title)} News Summary — {e(date_key)}</title>\n"
            f"      <link>{e(link)}</link>\n"
            f"      <description>{e(desc)}</description>\n"
            f"      <pubDate>{e(pub_date)}</pubDate>\n"
            f"      <guid isPermaLink=\"true\">{e(link)}</guid>\n"
            f"      <category>{e(title)}</category>\n"
            f"    </item>"
        ]

    @staticmethod
    def _wrap_rss_channel(title: str, link: str, description: str, items: List[str]) -> str:
        e = html.escape
        items_str = "\n".join(items)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
            "  <channel>\n"
            f"    <title>{e(title)}</title>\n"
            f"    <link>{e(link)}</link>\n"
            f"    <description>{e(description)}</description>\n"
            f"    <language>en-us</language>\n"
            f"{items_str}\n"
            "  </channel>\n"
            "</rss>\n"
        )

    # ── Internal linking helper ──

    def _build_recent_links(self, cat_key: str, current_date: str, max_links: int = 7) -> str:
        idx = self._read_index()
        dates = idx.get("dates", [])
        e = self._e
        links = []
        for entry in dates:
            d = entry.get("date", "")
            if d == current_date:
                continue
            if cat_key in entry.get("categories", []):
                links.append(f'      <li><a href="../{e(d)}/{e(cat_key)}.html">{e(d)}</a></li>')
            if len(links) >= max_links:
                break
        if not links:
            return ""
        cat_title = cat_key.replace("_", " ").title()
        return (
            f'    <h2>Recent {e(cat_title)} Reports</h2>\n'
            f'    <ul>\n'
            + "\n".join(links) + "\n"
            + "    </ul>\n"
        )

    # ── HTML renderers ──

    def _render_date_index(self, date_key: str, cats: Dict[str, Any], model: str) -> str:
        e = self._e
        cat_links = "\n".join(
            f'    <li><a href="{e(k)}.html">{e(c.get("title", k.title()))}</a></li>'
            for k, c in cats.items()
        )
        idx_desc = f"AI-generated news summaries for {date_key} across world, business, technology, sports, and science."
        idx_url = f"{self.BASE_URL}news/{date_key}/index.html"

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Daily News Summary — {e(date_key)} — TL;DR News</title>
  <meta name="description" content="{e(idx_desc)}">
  <meta name="robots" content="index, follow">
  <meta property="og:title" content="Daily News Summary — {e(date_key)}">
  <meta property="og:description" content="{e(idx_desc)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{e(idx_url)}">
  <meta property="og:site_name" content="TL;DR News">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="Daily News Summary — {e(date_key)}">
  <meta name="twitter:description" content="{e(idx_desc)}">
  <link rel="canonical" href="{e(idx_url)}">
  <link rel="alternate" type="application/rss+xml" title="TL;DR News" href="../feeds/all.xml">
  <script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  "name": "Daily News Summary — {e(date_key)}",
  "datePublished": "{e(date_key)}",
  "description": "{e(idx_desc)}",
  "publisher": {{ "@type": "Organization", "name": "TL;DR News", "url": "{self.BASE_URL}" }},
  "author": {{ "@type": "Organization", "name": "TL;DR News AI", "url": "{self.BASE_URL}" }}
}}
  </script>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 2em auto; padding: 0 1em;
           background: #0b0c10; color: #e9edf5; }}
    a {{ color: #25b7ff; }}
    li {{ margin-bottom: .5em; }}
  </style>
</head>
<body>
  <h1>Daily News Summary — {e(date_key)}</h1>
  <p>AI-generated reports for {e(date_key)}{f" using {e(model)}" if model else ""}.</p>
  <nav>
    <h2>Categories</h2>
    <ul>
{cat_links}
    </ul>
  </nav>
  <p><a href="../reports.html">← Back to interactive dashboard</a></p>
  <footer>
    <p>Generated by <a href="{e(self.BASE_URL)}">TL;DR News AI</a>. Daily AI-powered news intelligence.</p>
  </footer>
</body>
</html>
"""

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
        related_topics = rep.get("related_topics") or []

        page_title = f"{title} News Summary — {date_key}"
        meta_desc = key_takeaway or summary[:160]
        page_url = f"{self.BASE_URL}news/{date_key}/{cat_key}.html"

        # Schema.org JSON-LD — NewsArticle
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
                "url": self.BASE_URL,
            },
            "publisher": {
                "@type": "Organization",
                "name": "TL;DR News",
                "url": self.BASE_URL,
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": page_url,
            },
            "about": key_themes[:5],
            "keywords": ", ".join(related_topics[:6]) if related_topics else ", ".join(key_themes[:5]),
        }, ensure_ascii=False, indent=2)

        # FAQPage schema from notable headlines
        faq_ld = ""
        faq_entries = []
        for n in notable:
            headline = n.get("headline", "")
            why = n.get("why_it_matters", "")
            if headline and why:
                faq_entries.append({
                    "@type": "Question",
                    "name": f"Why does this matter: {headline}?",
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": why,
                    }
                })
        if faq_entries:
            faq_ld = json.dumps({
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": faq_entries[:10],
            }, ensure_ascii=False, indent=2)

        # OpenGraph meta tags
        og_tags = (
            f'  <meta property="og:title" content="{e(page_title)}">\n'
            f'  <meta property="og:description" content="{e(meta_desc)}">\n'
            f'  <meta property="og:type" content="article">\n'
            f'  <meta property="og:url" content="{e(page_url)}">\n'
            f'  <meta property="og:site_name" content="TL;DR News">\n'
            f'  <meta property="article:published_time" content="{e(date_key)}">\n'
            f'  <meta property="article:section" content="{e(title)}">\n'
            f'  <meta property="article:author" content="TL;DR News AI">\n'
            f'  <meta name="twitter:card" content="summary">\n'
            f'  <meta name="twitter:title" content="{e(page_title)}">\n'
            f'  <meta name="twitter:description" content="{e(meta_desc)}">\n'
        )

        # Render content sections
        themes_html = "".join(f"      <li>{e(t)}</li>\n" for t in key_themes)

        notable_html = ""
        for n in notable:
            hl = e(n.get("headline", ""))
            why = e(n.get("why_it_matters", ""))
            sig = e(n.get("signal", "Unclear"))
            notable_html += f"""
    <details>
      <summary><strong>{hl}</strong> [{sig}]</summary>
      <p>{why}</p>
    </details>
"""

        outlook_24 = "".join(f"        <li>{e(x)}</li>\n" for x in (outlook.get("next_24_72_hours") or []))
        outlook_4w = "".join(f"        <li>{e(x)}</li>\n" for x in (outlook.get("next_1_4_weeks") or []))
        watch = "".join(f"        <li>{e(x)}</li>\n" for x in (outlook.get("watch_list") or []))
        caveats_html = "".join(f"      <li>{e(c)}</li>\n" for c in caveats)

        items_html = ""
        for it in items:
            t = e(it.get("title", ""))
            u = e(it.get("url", "#"))
            pub = e(it.get("published", ""))
            items_html += f'    <p><a href="{u}" target="_blank" rel="noopener">{t}</a>'
            if pub:
                items_html += f' <small>({pub})</small>'
            items_html += "</p>\n"

        # Related topics section
        related_html = ""
        if related_topics:
            related_items = "".join(f"      <li>{e(t)}</li>\n" for t in related_topics)
            related_html = f"""
    <h2>Related Topics</h2>
    <ul>
{related_items}    </ul>
"""

        # Internal linking: recent reports for this category
        recent_links_html = self._build_recent_links(cat_key, date_key, max_links=7)

        sent_label = e(str(sent.get("label", "—")))
        sent_score = sent.get("score", "—")
        sent_score_str = f"{sent_score:.3f}" if isinstance(sent_score, (int, float)) else str(sent_score)

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{e(page_title)}</title>
  <meta name="description" content="{e(meta_desc)}">
  <meta name="robots" content="index, follow, max-snippet:-1">
  <link rel="canonical" href="{e(page_url)}">
  <link rel="alternate" type="application/rss+xml" title="TL;DR News — {e(title)}" href="../feeds/{cat_key}.xml">
  <link rel="alternate" type="application/rss+xml" title="TL;DR News — All Categories" href="../feeds/all.xml">
{og_tags}  <script type="application/ld+json">
{schema_ld}
  </script>
{f'''  <script type="application/ld+json">
{faq_ld}
  </script>''' if faq_ld else ''}
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 2em auto; padding: 0 1em;
           background: #0b0c10; color: #e9edf5; line-height: 1.6; }}
    a {{ color: #25b7ff; }}
    details {{ margin: .5em 0; padding: .5em; border: 1px solid rgba(255,255,255,.15); border-radius: 8px; }}
    summary {{ cursor: pointer; }}
    .outlook {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1em; }}
    .outlook-col {{ padding: 1em; border: 1px solid rgba(255,255,255,.15); border-radius: 8px; }}
    li {{ margin-bottom: .4em; }}
    .badge {{ display: inline-block; padding: .2em .6em; border-radius: 4px; font-size: .85em;
              border: 1px solid rgba(255,255,255,.2); margin-right: .5em; }}
    footer {{ margin-top: 2em; padding-top: 1em; border-top: 1px solid rgba(255,255,255,.15);
             color: #a4adbd; font-size: .85em; }}
  </style>
</head>
<body>
  <nav><a href="../reports.html">← Dashboard</a> | <a href="../{e(date_key)}/index.html">{e(date_key)} overview</a></nav>

  <article>
    <h1>{e(title)} News Summary</h1>
    <p>Date: <strong>{e(date_key)}</strong> | Source:
       <a href="{e(src.get('site_url', '#'))}" target="_blank" rel="noopener">{e(src.get('site_name', ''))}</a>
       (<a href="{e(src.get('feed_url', '#'))}" target="_blank" rel="noopener">RSS</a>)
    </p>

    <div>
      <span class="badge">Sentiment: <strong>{sent_label}</strong></span>
      <span class="badge">Score: <strong>{e(sent_score_str)}</strong></span>
      <span class="badge">Confidence: <strong>{e(str(outlook.get('confidence', '—')))}</strong></span>
    </div>

    {f'<blockquote><strong>Key takeaway:</strong> {e(key_takeaway)}</blockquote>' if key_takeaway else ''}

    <h2>Executive Summary</h2>
    <p>{e(summary)}</p>

    <h2>Key Themes</h2>
    <ul>
{themes_html}    </ul>

    <h2>Notable Headlines</h2>
{notable_html}

    <h2>Future Outlook</h2>
    <div class="outlook">
      <div class="outlook-col">
        <h3>Next 24–72 hours</h3>
        <ul>
{outlook_24}        </ul>
      </div>
      <div class="outlook-col">
        <h3>Next 1–4 weeks</h3>
        <ul>
{outlook_4w}        </ul>
      </div>
      <div class="outlook-col">
        <h3>Watch list</h3>
        <ul>
{watch}        </ul>
      </div>
    </div>

    <h2>Caveats</h2>
    <ul>
{caveats_html}    </ul>

    <h2>All Headlines</h2>
{items_html}
{related_html}
{recent_links_html}
  </article>

  <footer>
    <p>Generated by <a href="{e(self.BASE_URL)}">TL;DR News AI</a>{f' using {e(model)}' if model else ''} on {e(date_key)}. Daily AI-powered news intelligence.</p>
  </footer>
</body>
</html>
"""
