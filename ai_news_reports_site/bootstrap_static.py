#!/usr/bin/env python3
"""Bootstrap: generate archive HTML pages, RSS feed, and sitemap from all
existing report JSON files.  Run once from ai_news_reports_site/:

    python bootstrap_static.py
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.agents.publisher import PublisherAgent


def main() -> None:
    site_root = Path(__file__).resolve().parent
    publisher = PublisherAgent(site_root=site_root)

    reports_dir = site_root / "news" / "data" / "reports"
    date_keys   = sorted([p.stem for p in reports_dir.glob("*.json")], reverse=True)

    print(f"Found {len(date_keys)} report(s): {', '.join(date_keys)}\n")

    for date_key in date_keys:
        report_path = reports_dir / f"{date_key}.json"
        try:
            report       = json.loads(report_path.read_text(encoding="utf-8"))
            archive_path = publisher.write_archive_page(date_key, report)
            print(f"  archive: {archive_path.relative_to(site_root)}")
        except Exception as e:
            print(f"  ERROR {date_key}: {e}")

    sitemap_path = publisher.write_sitemap()
    print(f"\n  sitemap: {sitemap_path.relative_to(site_root)}")

    rss_path = publisher.write_rss_feed()
    print(f"  feed:    {rss_path.relative_to(site_root)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
