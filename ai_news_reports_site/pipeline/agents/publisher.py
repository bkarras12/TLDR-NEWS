from __future__ import annotations

import json
import os
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

