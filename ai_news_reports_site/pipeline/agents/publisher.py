from __future__ import annotations

import json
import os
import xml.sax.saxutils as saxutils
from pathlib import Path
from typing import Any, Dict, List

SITE_URL = os.environ.get("SITE_URL", "https://YOUR_DOMAIN").rstrip("/")


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

        self._write_sitemap(idx_dates)
        self._write_feed(idx_dates)

    def _write_sitemap(self, idx_dates: List[Dict[str, Any]]) -> None:
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            '  <url>',
            f'    <loc>{SITE_URL}/news/reports.html</loc>',
            '    <changefreq>daily</changefreq>',
            '    <priority>1.0</priority>',
            '  </url>',
        ]
        for entry in idx_dates:
            d = entry.get("date", "")
            if d:
                lines += [
                    '  <url>',
                    f'    <loc>{SITE_URL}/news/reports.html?date={d}</loc>',
                    f'    <lastmod>{d}</lastmod>',
                    '    <changefreq>never</changefreq>',
                    '    <priority>0.8</priority>',
                    '  </url>',
                ]
        lines.append('</urlset>')
        sitemap_path = self.site_root / "sitemap.xml"
        sitemap_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_feed(self, idx_dates: List[Dict[str, Any]]) -> None:
        """Generate an RSS 2.0 feed at site_root/feed.xml covering all indexed dates."""
        items: List[str] = []
        for entry in idx_dates[:20]:  # cap at 20 items for feed size
            d = entry.get("date", "")
            if not d:
                continue
            report_path = self.reports_dir / f"{d}.json"
            summary_parts: List[str] = []
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
                for cat_key in ["world", "business", "technology", "sports", "science"]:
                    cat = report.get("categories", {}).get(cat_key, {})
                    cat_summary = cat.get("ai_report", {}).get("summary", "")
                    cat_title = cat.get("title", cat_key.title())
                    if cat_summary:
                        summary_parts.append(f"<b>{cat_title}:</b> {cat_summary}")
            except Exception:
                summary_parts = [f"Daily briefing for {d}."]

            description = saxutils.escape(" ".join(summary_parts) or f"Daily AI news briefing for {d}.")
            title = saxutils.escape(f"TL;DR News — {d}")
            link = saxutils.escape(f"{SITE_URL}/news/reports.html?date={d}")
            # RFC 822 date (approximate — time unknown, use noon UTC)
            pub_date = f"{d}T12:00:00Z"
            items.append(
                f"  <item>\n"
                f"    <title>{title}</title>\n"
                f"    <link>{link}</link>\n"
                f"    <guid isPermaLink=\"true\">{link}</guid>\n"
                f"    <pubDate>{pub_date}</pubDate>\n"
                f"    <description>{description}</description>\n"
                f"  </item>"
            )

        channel_link = saxutils.escape(f"{SITE_URL}/news/reports.html")
        feed = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
            '  <channel>\n'
            f'    <title>TL;DR News — Daily AI Briefings</title>\n'
            f'    <link>{channel_link}</link>\n'
            f'    <atom:link href="{saxutils.escape(SITE_URL)}/feed.xml" rel="self" type="application/rss+xml" />\n'
            f'    <description>Daily AI-generated news intelligence across World, Business, Technology, Sports, and Science.</description>\n'
            f'    <language>en-us</language>\n'
            + "\n".join(items) + "\n"
            "  </channel>\n"
            "</rss>\n"
        )
        feed_path = self.site_root / "feed.xml"
        feed_path.write_text(feed, encoding="utf-8")
