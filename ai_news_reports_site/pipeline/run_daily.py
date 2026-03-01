from __future__ import annotations

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any, Dict

from openai import OpenAI

from pipeline.config import CATEGORIES
from pipeline.agents.rss_reader import RssReaderAgent
from pipeline.agents.curator import CuratorAgent
from pipeline.agents.sentiment import SentimentAgent
from pipeline.agents.report_writer import ReportWriterAgent
from pipeline.agents.publisher import PublisherAgent


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


def main() -> int:
    site_root = Path(__file__).resolve().parents[1]
    date_key = local_date_key()

    model = os.getenv("OPENAI_MODEL") or "gpt-4.1"
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is not set.", file=sys.stderr)
        print("Set it as an environment variable or as a GitHub Actions secret.", file=sys.stderr)
        return 2

    client = OpenAI()

    sentiment_agent = SentimentAgent()
    curator = CuratorAgent()

    categories_out: Dict[str, Any] = {}
    available_categories = []

    for key, cfg in CATEGORIES.items():
        print(f"[{key}] Fetching RSS: {cfg.feed_url}")
        reader = RssReaderAgent(cfg.feed_url, cfg.site_name)
        try:
            raw_items = reader.run(limit=cfg.max_items)
        except Exception as e:
            print(f"[{key}] ERROR fetching feed: {type(e).__name__}: {e}", file=sys.stderr)
            raw_items = []

        curated_items = CuratorAgent(max_items=cfg.max_items).run(raw_items)
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
            report = {
                "summary": "Report generation failed for this category.",
                "key_themes": ["Generation error", "Try again later", "Verify via links"],
                "notable_headlines": [],
                "future_outlook": {
                    "next_24_72_hours": ["Try again later."],
                    "next_1_4_weeks": ["Try again later."],
                    "watch_list": ["Pipeline reliability"],
                    "confidence": "Low",
                },
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

        if curated_items:
            available_categories.append(key)

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
