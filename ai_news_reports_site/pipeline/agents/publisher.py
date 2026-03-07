from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List


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

    # ------------------------------------------------------------------
    _SITE_URL    = "https://bkarras12.github.io/TLDR-NEWS"
    _REPORTS_URL = f"{_SITE_URL}/news/reports.html"

    def write_sitemap(self) -> Path:
        """Generate news/sitemap.xml from the current reports_index.json.

        Includes:
        - The main reports page (priority 1.0, changefreq daily)
        - One URL-with-query-param per report date (priority 0.7)
        - The raw JSON data file for each date (priority 0.5) so that
          AI crawlers that don't execute JavaScript can still discover
          and parse the structured report data directly.
        """
        if not self.index_path.exists():
            return self.site_root / "news" / "sitemap.xml"

        try:
            idx = json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return self.site_root / "news" / "sitemap.xml"

        dates  = [d["date"] for d in idx.get("dates", []) if d.get("date")]
        latest = idx.get("latest_date") or (dates[0] if dates else "")

        lines: list[str] = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]

        def url_block(loc: str, lastmod: str, changefreq: str, priority: str) -> str:
            return (
                "  <url>\n"
                f"    <loc>{loc}</loc>\n"
                f"    <lastmod>{lastmod}</lastmod>\n"
                f"    <changefreq>{changefreq}</changefreq>\n"
                f"    <priority>{priority}</priority>\n"
                "  </url>"
            )

        # Main reports page
        lines.append(url_block(self._REPORTS_URL, latest, "daily", "1.0"))

        for date in dates:
            # Report page for a specific date (crawlers can fetch with ?date=)
            lines.append(url_block(
                f"{self._REPORTS_URL}?date={date}",
                date, "never", "0.7",
            ))
            # Raw JSON data file — directly machine-readable; valuable for GEO
            lines.append(url_block(
                f"{self._SITE_URL}/news/data/reports/{date}.json",
                date, "never", "0.5",
            ))

        # Index file itself
        lines.append(url_block(
            f"{self._SITE_URL}/news/data/reports_index.json",
            latest, "daily", "0.4",
        ))

        lines.append("</urlset>")

        sitemap_path = self.site_root / "news" / "sitemap.xml"
        sitemap_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return sitemap_path
