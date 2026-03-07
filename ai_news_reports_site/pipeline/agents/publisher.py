from __future__ import annotations

import html as _html
import json
from datetime import datetime, timezone
from email.utils import format_datetime as _fmt_rfc2822
from pathlib import Path
from typing import Any, Dict, List, Optional


_CATEGORY_ORDER = ["world", "business", "technology", "sports", "science"]


class PublisherAgent:
    def __init__(self, site_root: Path):
        self.site_root   = site_root
        self.reports_dir = self.site_root / "news" / "data" / "reports"
        self.index_path  = self.site_root / "news" / "data" / "reports_index.json"

        self.reports_dir.mkdir(parents=True, exist_ok=True)
        (self.site_root / "news" / "data").mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Core write / index methods
    # ------------------------------------------------------------------

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

        # Remove existing entry for the same date (handles reruns)
        idx_dates = [d for d in idx.get("dates", []) if d.get("date") != date_key]

        # Prepend new entry (newest first)
        idx_dates.insert(0, {"date": date_key, "categories": available_categories})
        idx_dates = idx_dates[:keep_last]

        idx["latest_date"] = idx_dates[0]["date"] if idx_dates else date_key
        idx["dates"] = idx_dates

        self.index_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ------------------------------------------------------------------
    # Shared constants
    # ------------------------------------------------------------------

    _SITE_URL    = "https://bkarras12.github.io/TLDR-NEWS"
    _REPORTS_URL = f"{_SITE_URL}/news/reports.html"

    def _load_index(self) -> Dict[str, Any]:
        if not self.index_path.exists():
            return {"latest_date": None, "dates": []}
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return {"latest_date": None, "dates": []}

    def _adjacent_dates(self, date_key: str) -> tuple[Optional[str], Optional[str]]:
        """Return (prev_date, next_date) for date_key from the index.

        Index is newest-first so:
          next (newer)  = lower index position
          prev (older)  = higher index position
        """
        dates = [d["date"] for d in self._load_index().get("dates", []) if d.get("date")]
        if date_key not in dates:
            return None, None
        pos = dates.index(date_key)
        prev_date = dates[pos + 1] if pos + 1 < len(dates) else None
        next_date = dates[pos - 1] if pos > 0        else None
        return prev_date, next_date

    # ------------------------------------------------------------------
    # Static HTML archive pages
    # ------------------------------------------------------------------

    _ARCHIVE_CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: #06080f; color: #dde4f0;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 15px; line-height: 1.65;
}
a { color: #00e5ff; text-decoration: none; }
a:hover { text-decoration: underline; }
.page { max-width: 860px; margin: 0 auto; padding: 24px 20px 60px; }
.site-link {
  display: inline-block; margin-bottom: 24px;
  font-family: monospace; font-size: 12px;
  letter-spacing: .06em; color: #5c6a84;
}
.site-link:hover { color: #00e5ff; text-decoration: none; }
h1 { font-size: 26px; font-weight: 700; letter-spacing: -.01em; margin-bottom: 6px; }
.date-meta { font-family: monospace; font-size: 12px; color: #5c6a84; margin-bottom: 20px; }
.arc-nav {
  display: flex; gap: 16px; flex-wrap: wrap;
  padding: 11px 16px;
  border: 1px solid rgba(255,255,255,.07);
  border-radius: 8px;
  background: rgba(255,255,255,.02);
  font-family: monospace; font-size: 12px;
  margin-bottom: 28px;
}
.arc-nav a { color: #7a8ba6; }
.arc-nav a:hover { color: #00e5ff; text-decoration: none; }
.cta-box { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 32px; }
.cta {
  display: inline-block; padding: 9px 18px;
  background: rgba(0,229,255,.12);
  border: 1px solid rgba(0,229,255,.28);
  border-radius: 8px; color: #00e5ff;
  font-family: monospace; font-size: 12px; letter-spacing: .06em;
}
.cta:hover { background: rgba(0,229,255,.22); text-decoration: none; }
.cta.muted {
  background: rgba(255,255,255,.03);
  border-color: rgba(255,255,255,.10); color: #7a8ba6;
}
.cta.muted:hover { color: #dde4f0; text-decoration: none; }
.cat-section { border-top: 1px solid rgba(255,255,255,.07); padding-top: 28px; margin-top: 28px; }
.cat-header { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
h2 { font-size: 20px; font-weight: 700; }
.badge {
  display: inline-block; padding: 3px 10px; border-radius: 999px;
  font-size: 11px; font-family: monospace; letter-spacing: .05em;
  border: 1px solid rgba(255,255,255,.14); background: rgba(255,255,255,.04);
}
.badge.positive { border-color: rgba(0,193,124,.40); color: #00c17c; }
.badge.negative { border-color: rgba(255,82,82,.40); color: #ff5252; }
.badge.neutral  { border-color: rgba(255,255,255,.15); color: #7a8ba6; }
.summary { color: #b0bcd4; margin-bottom: 14px; }
h3 {
  font-family: monospace; font-size: 10px;
  letter-spacing: .14em; text-transform: uppercase;
  color: #5c6a84; margin: 18px 0 8px;
}
ul { padding-left: 18px; }
li { margin-bottom: 7px; font-size: 14px; }
.signal {
  display: inline-block; margin-left: 6px; padding: 1px 7px;
  border-radius: 999px; font-size: 10px; font-family: monospace;
  border: 1px solid rgba(255,255,255,.10); vertical-align: middle;
}
.signal.opportunity { border-color: rgba(0,193,124,.35); color: #00c17c; }
.signal.risk        { border-color: rgba(255,82,82,.35);  color: #ff5252; }
.signal.unclear     { color: #5c6a84; }
.why {
  display: block; margin-top: 3px; font-size: 12px;
  color: #5c6a84; padding-left: 2px;
}
.source-line { margin-top: 16px; font-size: 12px; color: #5c6a84; font-family: monospace; }
.footer {
  margin-top: 48px; padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,.07);
  font-family: monospace; font-size: 11px; color: #5c6a84;
  display: flex; flex-wrap: wrap; gap: 16px;
}"""

    def write_archive_page(self, date_key: str, report: Dict[str, Any]) -> Path:
        """Write a static, JS-free HTML archive page for one day's report.

        Saved to news/archives/{date_key}.html.  Fully crawlable by
        search engines and AI systems that skip JavaScript execution.
        """
        archives_dir = self.site_root / "news" / "archives"
        archives_dir.mkdir(parents=True, exist_ok=True)

        prev_date, next_date = self._adjacent_dates(date_key)
        cats  = report.get("categories") or {}
        model = report.get("model", "gpt-4o-mini")

        # ── Helpers ────────────────────────────────────────────────────
        def h(text: Any, quote: bool = False) -> str:
            """HTML-escape text; set quote=True for attribute values."""
            return _html.escape(str(text or ""), quote=quote)

        def hq(text: Any) -> str:
            return h(text, quote=True)

        # ── Meta description ───────────────────────────────────────────
        meta_desc = ""
        for key in _CATEGORY_ORDER:
            summary = ((cats.get(key) or {}).get("ai_report") or {}).get("summary") or ""
            if summary:
                meta_desc = summary[:155].rstrip() + ("…" if len(summary) > 155 else "")
                break
        if not meta_desc:
            meta_desc = f"TLDR News AI intelligence report for {date_key}."

        # ── JSON-LD schema ─────────────────────────────────────────────
        keywords: list[str] = []
        citations: list[dict] = []
        for key in _CATEGORY_ORDER:
            cat = cats.get(key) or {}
            themes = (cat.get("ai_report") or {}).get("key_themes") or []
            if isinstance(themes, list):
                keywords.extend(str(t) for t in themes)
            for item in (cat.get("items") or [])[:3]:
                if item.get("title") and item.get("url"):
                    citations.append({
                        "@type": "NewsArticle",
                        "headline": item["title"],
                        "url": item["url"],
                        "publisher": {"@type": "Organization", "name": item.get("source", "")},
                    })

        archive_url = f"{self._SITE_URL}/news/archives/{date_key}.html"
        schema = json.dumps({
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": f"TLDR News Intelligence \u2014 {date_key}",
            "description": meta_desc,
            "datePublished": date_key,
            "dateModified": date_key,
            "url": archive_url,
            "inLanguage": "en",
            "author": {
                "@type": "Organization",
                "name": "TLDR News AI Pipeline",
                "url": f"{self._SITE_URL}/",
            },
            "publisher": {
                "@type": "Organization",
                "name": "TLDR News",
                "url": f"{self._SITE_URL}/",
                "logo": {"@type": "ImageObject", "url": f"{self._SITE_URL}/news/tldr_logo.png"},
            },
            "keywords": ", ".join(dict.fromkeys(keywords))[:500],
            "citation": citations[:15],
            "mainEntityOfPage": {"@type": "WebPage", "@id": archive_url},
        }, ensure_ascii=False, indent=2)

        # ── Prev / next nav ────────────────────────────────────────────
        nav_parts: list[str] = []
        if next_date:
            nav_parts.append(f'<a href="{hq(next_date)}.html">\u2190 {h(next_date)}</a>')
        if prev_date:
            nav_parts.append(f'<a href="{hq(prev_date)}.html">{h(prev_date)} \u2192</a>')
        nav_html = (
            '<nav class="arc-nav">'
            '<strong style="color:#5c6a84">Archives:</strong> '
            + " &middot; ".join(nav_parts)
            + "</nav>"
        ) if nav_parts else ""

        # ── Sentiment badge ────────────────────────────────────────────
        def sentiment_badge(label: str, score: Any) -> str:
            cls = "neutral"
            if isinstance(score, (int, float)) and not isinstance(score, bool):
                if   score >  0.1: cls = "positive"
                elif score < -0.1: cls = "negative"
            score_str = (
                f"{score:+.3f}"
                if isinstance(score, (int, float)) and not isinstance(score, bool)
                else "\u2014"
            )
            em_dash = "\u2014"
            label_safe = h(label or em_dash)
            return f'<span class="badge {h(cls)}">{label_safe} {h(score_str)}</span>'

        # ── Category sections ──────────────────────────────────────────
        sections_html = ""
        for cat_key in _CATEGORY_ORDER:
            cat = cats.get(cat_key)
            if not cat:
                continue
            ai   = cat.get("ai_report") or {}
            sent = cat.get("sentiment") or {}
            src  = cat.get("source")    or {}
            title = h(cat.get("title", cat_key.title()))

            summary = h(ai.get("summary") or "")

            themes_html = ""
            for t in (ai.get("key_themes") or [])[:8]:
                themes_html += f"<li>{h(t)}</li>\n"

            notable_html = ""
            items_lookup = {
                (item.get("title") or "").lower(): item.get("url") or ""
                for item in (cat.get("items") or [])
            }
            for n in (ai.get("notable_headlines") or [])[:8]:
                if not isinstance(n, dict):
                    continue
                headline = (n.get("headline") or n.get("title") or "").strip()
                if not headline:
                    continue
                # Best-effort URL match
                url = ""
                hl_lower = headline.lower()
                for item_title, item_url in items_lookup.items():
                    if item_title and (item_title in hl_lower or hl_lower in item_title):
                        url = item_url
                        break

                why       = h(n.get("why_it_matters") or "")
                signal    = (n.get("signal") or "Unclear").strip()
                sig_cls   = signal.lower() if signal.lower() in ("opportunity", "risk") else "unclear"
                linked    = f'<a href="{hq(url)}">{h(headline)}</a>' if url else h(headline)
                why_span  = f'<span class="why">{why}</span>' if why else ""
                notable_html += (
                    f'<li>{linked}'
                    f'<span class="signal {h(sig_cls)}">{h(signal)}</span>'
                    f'{why_span}</li>\n'
                )

            src_name = h(src.get("site_name") or "")
            src_url  = hq(src.get("site_url") or "#")
            badge    = sentiment_badge(sent.get("label"), sent.get("score"))

            sections_html += f"""
  <section class="cat-section" id="{h(cat_key)}">
    <div class="cat-header">
      <h2>{title}</h2>
      {badge}
    </div>
    <p class="summary">{summary}</p>
    {"<h3>Key Themes</h3><ul>" + themes_html + "</ul>" if themes_html else ""}
    {"<h3>Notable Headlines</h3><ul>" + notable_html + "</ul>" if notable_html else ""}
    <p class="source-line">Source: <a href="{src_url}">{src_name}</a></p>
  </section>"""

        # ── Full page ──────────────────────────────────────────────────
        spa_url  = hq(f"{self._REPORTS_URL}?date={date_key}")
        json_url = hq(f"{self._SITE_URL}/news/data/reports/{date_key}.json")
        feed_url = f"{self._SITE_URL}/news/feed.xml"

        page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>TLDR News Intelligence &middot; {h(date_key)}</title>
  <meta name="description" content="{hq(meta_desc)}" />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{hq(archive_url)}" />
  <link rel="alternate" type="application/rss+xml" title="TLDR News Daily Intelligence" href="{hq(feed_url)}" />
  <script type="application/ld+json">
{schema}
  </script>
  <style>
{self._ARCHIVE_CSS}
  </style>
</head>
<body>
<div class="page">

  <a class="site-link" href="../reports.html">&larr; TLDR News &middot; Live Reports</a>

  <h1>TLDR News Intelligence</h1>
  <div class="date-meta">{h(date_key)} &middot; AI-powered daily news analysis &middot; Model: {h(model)}</div>

  {nav_html}

  <div class="cta-box">
    <a class="cta" href="{spa_url}">Open interactive report &rarr;</a>
    <a class="cta muted" href="{json_url}">Raw JSON data</a>
  </div>

  {sections_html}

  <footer class="footer">
    <span>Generated by TLDR News AI Pipeline &middot; {h(model)}</span>
    <a href="../reports.html">&larr; Back to live reports</a>
    <a href="{json_url}">View raw JSON</a>
  </footer>

</div>
</body>
</html>"""

        out_path = archives_dir / f"{date_key}.html"
        out_path.write_text(page, encoding="utf-8")
        return out_path

    # ------------------------------------------------------------------
    # Sitemap (updated to include archive pages at priority 0.8)
    # ------------------------------------------------------------------

    def write_sitemap(self) -> Path:
        """Generate news/sitemap.xml.

        Priority tiers:
          1.0 — main SPA reports page  (daily)
          0.8 — static archive HTML    (never — immutable per date)
          0.7 — SPA ?date= URL         (never)
          0.5 — raw JSON data file     (never)
          0.4 — reports_index.json     (daily)
        """
        if not self.index_path.exists():
            return self.site_root / "news" / "sitemap.xml"
        try:
            idx = json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return self.site_root / "news" / "sitemap.xml"

        dates  = [d["date"] for d in idx.get("dates", []) if d.get("date")]
        latest = idx.get("latest_date") or (dates[0] if dates else "")

        def url_block(loc: str, lastmod: str, changefreq: str, priority: str) -> str:
            return (
                "  <url>\n"
                f"    <loc>{loc}</loc>\n"
                f"    <lastmod>{lastmod}</lastmod>\n"
                f"    <changefreq>{changefreq}</changefreq>\n"
                f"    <priority>{priority}</priority>\n"
                "  </url>"
            )

        lines: list[str] = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            # Main SPA page
            url_block(self._REPORTS_URL, latest, "daily", "1.0"),
        ]

        # Static archive pages — highest per-date priority (real HTML)
        for date in dates:
            lines.append(url_block(
                f"{self._SITE_URL}/news/archives/{date}.html",
                date, "never", "0.8",
            ))

        for date in dates:
            lines.append(url_block(f"{self._REPORTS_URL}?date={date}", date, "never", "0.7"))
            lines.append(url_block(
                f"{self._SITE_URL}/news/data/reports/{date}.json", date, "never", "0.5",
            ))

        lines.append(url_block(
            f"{self._SITE_URL}/news/data/reports_index.json", latest, "daily", "0.4",
        ))
        lines.append("</urlset>")

        sitemap_path = self.site_root / "news" / "sitemap.xml"
        sitemap_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return sitemap_path

    # ------------------------------------------------------------------
    # RSS feed — 1 daily digest item
    # ------------------------------------------------------------------

    def write_rss_feed(self, max_items: int = 30) -> Path:
        """Generate news/feed.xml — RSS 2.0 daily digest.

        One <item> per day combining all 5 categories into a single digest.
        Keeps up to max_items days (default 30).
        """
        idx    = self._load_index()
        dates  = [d["date"] for d in idx.get("dates", []) if d.get("date")][:max_items]
        latest = idx.get("latest_date") or (dates[0] if dates else "")

        def h(text: Any) -> str:
            return _html.escape(str(text or ""), quote=False)

        def rfc2822(date_str: str) -> str:
            try:
                y, m, d = (int(p) for p in date_str.split("-"))
                return _fmt_rfc2822(datetime(y, m, d, 12, 0, 0, tzinfo=timezone.utc))
            except Exception:
                return ""

        items_xml = ""
        for date in dates:
            json_path = self.reports_dir / f"{date}.json"
            if not json_path.exists():
                continue
            try:
                report = json.loads(json_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            cats = report.get("categories") or {}

            # Item title: date + world / tech tone hints
            world_label = ((cats.get("world")      or {}).get("sentiment") or {}).get("label") or ""
            tech_label  = ((cats.get("technology") or {}).get("sentiment") or {}).get("label") or ""
            tone_parts  = [
                f"{world_label.lower()} world" if world_label else "",
                f"{tech_label.lower()} tech"   if tech_label  else "",
            ]
            tone       = " \u00b7 ".join(p for p in tone_parts if p)
            item_title = f"TLDR Intelligence \u00b7 {date}" + (f" \u2014 {tone}" if tone else "")

            archive_url = f"{self._SITE_URL}/news/archives/{date}.html"

            # Description: one summary paragraph per category
            desc_parts: list[str] = []
            content_parts: list[str] = []
            for cat_key in _CATEGORY_ORDER:
                cat      = cats.get(cat_key)
                if not cat:
                    continue
                cat_title = h(cat.get("title") or cat_key.title())
                ai        = cat.get("ai_report") or {}
                summary   = h((ai.get("summary") or "").strip())

                if summary:
                    desc_parts.append(f"<p><strong>{cat_title}:</strong> {summary}</p>")

                headlines: list[str] = []
                for n in (ai.get("notable_headlines") or [])[:3]:
                    if not isinstance(n, dict):
                        continue
                    hl = h((n.get("headline") or n.get("title") or "").strip())
                    if hl:
                        sig  = h(n.get("signal") or "")
                        headlines.append(f"<li>{hl}{(' &middot; ' + sig) if sig else ''}</li>")

                if summary or headlines:
                    content_parts.append(
                        f"<h3>{cat_title}</h3>"
                        + (f"<p>{summary}</p>" if summary else "")
                        + (f"<ul>{''.join(headlines)}</ul>" if headlines else "")
                    )

            read_more    = f'<p><a href="{h(archive_url)}">Read full report &rarr;</a></p>'
            desc_cdata   = "\n".join(desc_parts) + "\n" + read_more
            content_cdata = "\n".join(content_parts) + "\n" + read_more

            pub_date_str = rfc2822(date)
            items_xml += (
                f"\n  <item>\n"
                f"    <title>{h(item_title)}</title>\n"
                f"    <link>{h(archive_url)}</link>\n"
                f"    <guid isPermaLink=\"true\">{h(archive_url)}</guid>\n"
                + (f"    <pubDate>{h(pub_date_str)}</pubDate>\n" if pub_date_str else "")
                + f"    <dc:creator>TLDR News AI Pipeline</dc:creator>\n"
                f"    <description><![CDATA[{desc_cdata}]]></description>\n"
                f"    <content:encoded><![CDATA[{content_cdata}]]></content:encoded>\n"
                f"  </item>"
            )

        last_build = rfc2822(latest) if latest else ""
        feed = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0"\n'
            '     xmlns:atom="http://www.w3.org/2005/Atom"\n'
            '     xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
            '     xmlns:content="http://purl.org/rss/1.0/modules/content/">\n'
            "  <channel>\n"
            "    <title>TLDR News &#8212; AI Intelligence Reports</title>\n"
            f"    <link>{self._REPORTS_URL}</link>\n"
            "    <description>Daily AI-generated intelligence across world news, business, technology, sports, and science.</description>\n"
            "    <language>en-us</language>\n"
            + (f"    <lastBuildDate>{h(last_build)}</lastBuildDate>\n" if last_build else "")
            + f'    <atom:link href="{self._SITE_URL}/news/feed.xml" rel="self" type="application/rss+xml"/>\n'
            "    <image>\n"
            f"      <url>{self._SITE_URL}/news/tldr_logo.png</url>\n"
            "      <title>TLDR News</title>\n"
            f"      <link>{self._REPORTS_URL}</link>\n"
            "    </image>\n"
            + items_xml
            + "\n  </channel>\n</rss>\n"
        )

        feed_path = self.site_root / "news" / "feed.xml"
        feed_path.write_text(feed, encoding="utf-8")
        return feed_path
