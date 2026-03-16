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


def _find_latest_report(reports_dir: Path) -> Path | None:
    """Find the most recent report file by date in the filename."""
    if not reports_dir.exists():
        return None
    candidates = sorted(reports_dir.glob("*.json"), key=lambda p: p.stem, reverse=True)
    return candidates[0] if candidates else None


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.post_tweets <category_key>", file=sys.stderr)
        return 1

    cat_key = sys.argv[1]
    dry_run = os.getenv("X_DRY_RUN", "").strip().lower() == "true"

    date_key = _today_key()
    site_root = Path(__file__).resolve().parents[1]
    reports_dir = site_root / "news" / "data" / "reports"
    report_path = reports_dir / f"{date_key}.json"

    # If today's report doesn't exist (cron delayed past midnight), use the latest available
    if not report_path.exists():
        latest = _find_latest_report(reports_dir)
        if latest is None:
            print(f"No report found for {date_key} and no fallback available", file=sys.stderr)
            return 1
        report_path = latest
        print(f"No report for {date_key}, falling back to {latest.stem}")

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
    except tweepy.Forbidden as e:
        err_msg = str(e).lower()
        if "duplicate" in err_msg:
            print(f"[{key}] Tweet already posted (duplicate content). Skipping.")
            return 0
        # Daily tweet limit or other quota errors — not actionable, skip gracefully
        if "limit" in err_msg or "quota" in err_msg or "capacity" in err_msg:
            print(f"[{key}] Daily tweet limit reached, skipping: {e}")
            return 0
        print(f"[{key}] ERROR posting tweet: Forbidden: {e}", file=sys.stderr)
        return 1
    except tweepy.TooManyRequests as e:
        print(f"[{key}] Rate limited, skipping: {e}")
        return 0
    except Exception as e:
        print(f"[{key}] ERROR posting tweet: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
