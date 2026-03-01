from __future__ import annotations

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any, Dict, List

from openai import OpenAI

from pipeline.config import CATEGORIES
from pipeline.agents.rss_reader import RssReaderAgent
from pipeline.agents.curator import CuratorAgent
from pipeline.agents.sentiment import SentimentAgent
from pipeline.agents.report_writer import ReportWriterAgent
from pipeline.agents.publisher import PublisherAgent
from pipeline.agents.base import NewsItem


TZ = "America/Denver"


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def local_date_key() -> str:
    return datetime.now(ZoneInfo(TZ)).date().isoformat()


def to_item_dict(it) -> Dict[str, Any]:
    return {
        "title": it.title,
        "url": it.url,
        "published": it.published,
        "summary": it.summary,
        "source": it.source,
    }


def _extract_items_from_report(path: Path) -> Dict[str, List[NewsItem]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    categories = data.get("categories") or {}
    out: Dict[str, List[NewsItem]] = {}

    for cat_key, cat_data in categories.items():
        raw_items = cat_data.get("items") or []
        items: List[NewsItem] = []
        for row in raw_items:
            title = (row.get("title") or "").strip()
            url = (row.get("url") or "").strip()
            if not title or not url:
                continue
            items.append(
                NewsItem(
                    title=title,
                    url=url,
                    published=row.get("published"),
                    summary=row.get("summary"),
                    source=row.get("source"),
                )
            )
        if items:
            out[cat_key] = items

    return out


def _load_backup_items(site_root: Path, date_key: str) -> Dict[str, List[NewsItem]]:
    reports_dir = site_root / "news" / "data" / "reports"
    if not reports_dir.exists():
        return {}

    report_paths = sorted(reports_dir.glob("*.json"), key=lambda p: p.stem, reverse=True)
    preferred = reports_dir / f"{date_key}.json"
    if preferred in report_paths:
        report_paths.remove(preferred)
        report_paths.insert(0, preferred)

    for path in report_paths:
        try:
            out = _extract_items_from_report(path)
            if out:
                print(f"Loaded backup headlines from: {path}")
                return out
        except Exception:
            continue

    return {}


def main() -> int:
    site_root = Path(__file__).resolve().parents[1]
    date_key = local_date_key()

    model = os.getenv("OPENAI_MODEL") or "gpt-4.1"
    api_key = os.getenv("OPENAI_API_KEY")
    in_github_actions = os.getenv("GITHUB_ACTIONS") == "true"

    if api_key:
        client = OpenAI(api_key=api_key)
    elif in_github_actions:
        print("ERROR: OPENAI_API_KEY is not set in GitHub Actions.", file=sys.stderr)
        print("Set repository/environment secret OPENAI_API_KEY for workflow runs.", file=sys.stderr)
        return 2
    else:
        client = None
        print(
            "OPENAI_API_KEY is not set. Proceeding with deterministic local report generation.",
            file=sys.stderr,
        )

    sentiment_agent = SentimentAgent()

    categories_out: Dict[str, Any] = {}
    backup_items = _load_backup_items(site_root=site_root, date_key=date_key)

    for key, cfg in CATEGORIES.items():
        print(f"[{key}] Fetching RSS: {cfg.feed_url}")
        reader = RssReaderAgent(cfg.feed_url, cfg.site_name)
        try:
            raw_items = reader.run(limit=cfg.max_items)
        except Exception as e:
            print(f"[{key}] ERROR fetching feed: {type(e).__name__}: {e}", file=sys.stderr)
            raw_items = []

        curated_items = CuratorAgent(max_items=cfg.max_items).run(raw_items)
        if not curated_items and backup_items.get(key):
            curated_items = CuratorAgent(max_items=cfg.max_items).run(list(backup_items[key]))
            print(f"[{key}] Using {len(curated_items)} backup headlines from previous report")
        sentiment = sentiment_agent.run(curated_items)

        writer = ReportWriterAgent(client=client, model=model)
        try:
            report = writer.run(
                category_title=cfg.title,
                source_name=cfg.site_name,
                items=curated_items,
                sentiment=sentiment,
            )
        except Exception as e:
            print(f"[{key}] ERROR writing report: {type(e).__name__}: {e}", file=sys.stderr)

            summary_text = "Report generation failed for this category."
            outlook_data = {
                "next_24_72_hours": ["Try again later."],
                "next_1_4_weeks": ["Try again later."],
                "watch_list": ["Pipeline reliability"],
                "confidence": "Low",
            }

            try:
                summary_text = writer.executive_summary_agent.run(
                    category_title=cfg.title,
                    source_name=cfg.site_name,
                    items=curated_items,
                    sentiment=sentiment,
                )
            except Exception:
                pass

            try:
                outlook_data = writer.future_outlook_agent.run(
                    category_title=cfg.title,
                    source_name=cfg.site_name,
                    items=curated_items,
                    sentiment=sentiment,
                )
            except Exception:
                pass

            report = {
                "summary": summary_text,
                "key_themes": ["Generation error", "Try again later", "Verify via links"],
                "notable_headlines": [],
                "future_outlook": outlook_data,
                "caveats": [
                    "OpenAI generation failed for this category.",
                    "This is an automated report; verify details via the source links.",
                ],
            }

        categories_out[key] = {
            "key": key,
            "title": cfg.title,
            "source": {
                "site_name": cfg.site_name,
                "site_url": cfg.site_url,
                "feed_url": cfg.feed_url,
            },
            "sentiment": {
                "score": sentiment.score,
                "label": sentiment.label,
                "rationale": sentiment.rationale,
            },
            "items": [to_item_dict(i) for i in curated_items],
            "ai_report": report,
        }


    daily_report = {
        "date": date_key,
        "generated_at_utc": iso_utc_now(),
        "timezone": TZ,
        "model": model,
        "categories": categories_out,
    }

    publisher = PublisherAgent(site_root=site_root)
    out_path = publisher.write_daily_report(date_key, daily_report)
    publisher.update_index(date_key=date_key, available_categories=list(CATEGORIES.keys()))

    print(f"Saved daily report to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
