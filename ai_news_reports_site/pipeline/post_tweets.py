"""Post a single category tweet to X.

Usage:
    python -m pipeline.post_tweets <category_key>

Example:
    python -m pipeline.post_tweets world
    python -m pipeline.post_tweets technology

Environment variables:
    X_CONSUMER_KEY     - OAuth 1.0a consumer key (API key)
    X_CONSUMER_SECRET  - OAuth 1.0a consumer secret (API key secret)
    X_ACCESS_TOKEN     - OAuth 1.0a access token
    X_ACCESS_SECRET    - OAuth 1.0a access token secret
    X_DRY_RUN          - Set to "true" to print without posting
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


TZ = "America/Denver"


def _today_key() -> str:
    return datetime.now(ZoneInfo(TZ)).strftime("%Y-%m-%d")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.post_tweets <category_key>", file=sys.stderr)
        return 1

    cat_key = sys.argv[1]
    dry_run = os.getenv("X_DRY_RUN", "").strip().lower() == "true"

    date_key = _today_key()
    site_root = Path(__file__).resolve().parents[1]
    report_path = site_root / "news" / "data" / "reports" / f"{date_key}.json"

    if not report_path.exists():
        print(f"No report found for {date_key} at {report_path}", file=sys.stderr)
        return 1

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    categories = report.get("categories", {})

    if cat_key not in categories:
        print(f"Category '{cat_key}' not found in report. Available: {', '.join(categories.keys())}", file=sys.stderr)
        return 1

    key = cat_key
    cat_data = categories[key]
    tweet_text = cat_data.get("tweet_text", "")

    if not tweet_text:
        print(f"[{key}] No tweet_text found, skipping.", file=sys.stderr)
        return 0

    print(f"[{key}] Tweet ({len(tweet_text)} chars):\n{tweet_text}\n")

    if dry_run:
        print("[DRY RUN] Tweet not posted.")
        return 0

    # Post to X
    consumer_key = os.getenv("X_CONSUMER_KEY", "").strip()
    consumer_secret = os.getenv("X_CONSUMER_SECRET", "").strip()
    access_token = os.getenv("X_ACCESS_TOKEN", "").strip()
    access_secret = os.getenv("X_ACCESS_SECRET", "").strip()

    if not all([consumer_key, consumer_secret, access_token, access_secret]):
        print("ERROR: Missing X API credentials. Set X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET.", file=sys.stderr)
        return 1

    import tweepy

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )

    try:
        response = client.create_tweet(text=tweet_text)
        tweet_id = response.data["id"]
        print(f"[{key}] Posted tweet: https://x.com/tldrnewsusa/status/{tweet_id}")
    except Exception as e:
        print(f"[{key}] ERROR posting tweet: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
