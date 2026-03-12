"""Find popular trending tweets and quote-tweet them with AI commentary.

X API does not allow replying to tweets unless you've been mentioned or
engaged by the author. Quote tweets work on any public tweet — same
engagement benefit, no restriction.

Usage:
    python -m pipeline.post_replies

Environment variables:
    X_CONSUMER_KEY     - OAuth 1.0a consumer key
    X_CONSUMER_SECRET  - OAuth 1.0a consumer secret
    X_ACCESS_TOKEN     - OAuth 1.0a access token
    X_ACCESS_SECRET    - OAuth 1.0a access token secret
    X_BEARER_TOKEN     - OAuth 2.0 bearer token (for search)
    OPENAI_API_KEY     - OpenAI API key (for commentary generation)
    OPENAI_MODEL       - Model override (default: gpt-4o-mini)
    X_DRY_RUN          - Set to "true" to log without posting
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from pipeline.agents.reply_writer import ReplyWriterAgent

# ── Configuration ──
MAX_QUOTES_PER_RUN = 1
MIN_LIKES = 50
MIN_RETWEETS = 10
MAX_TWEET_AGE_HOURS = 12
QUOTE_DELAY_SECONDS = 90
QUOTED_TWEETS_RETENTION_DAYS = 7
SELF_USERNAME = "tldrnewsusa"
TZ = "America/Denver"

# Profanity filter for inbound tweets
_PROFANITY = {
    "fuck", "shit", "bitch", "ass", "damn", "crap", "dick", "piss",
    "bastard", "slut", "whore", "nigger", "faggot", "retard",
}


def _today_key() -> str:
    return datetime.now(ZoneInfo(TZ)).strftime("%Y-%m-%d")


def _load_report(site_root: Path, date_key: str) -> Optional[Dict[str, Any]]:
    """Load today's daily report JSON."""
    report_path = site_root / "news" / "data" / "reports" / f"{date_key}.json"
    if not report_path.exists():
        print(f"[post_replies] No report for {date_key}", file=sys.stderr)
        return None
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_search_terms(report: Dict[str, Any]) -> List[str]:
    """Extract search terms from trending topics and notable headlines."""
    terms: List[str] = []

    # 1. Trending topics (cross-category keywords from pipeline)
    for topic in report.get("trending_topics", [])[:8]:
        topic = topic.strip()
        if len(topic) >= 3:
            terms.append(topic)

    # 2. Notable headline keywords (names, companies, events)
    categories = report.get("categories", {})
    for cat_data in categories.values():
        ai = cat_data.get("ai_report", {})
        for nh in ai.get("notable_headlines", [])[:3]:
            headline = nh.get("headline", "")
            proper_nouns = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", headline)
            for noun in proper_nouns[:2]:
                if noun not in terms:
                    terms.append(noun)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: List[str] = []
    for t in terms:
        lower = t.lower()
        if lower not in seen:
            seen.add(lower)
            unique.append(t)
    return unique[:15]


def _has_profanity(text: str) -> bool:
    words = set(re.sub(r"[^a-zA-Z\s]", "", text.lower()).split())
    return bool(words & _PROFANITY)


def _match_category(tweet_text: str, report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find the most relevant category for a tweet based on keyword overlap."""
    categories = report.get("categories", {})
    best_cat = None
    best_score = 0
    tweet_words = set(tweet_text.lower().split())

    for cat_data in categories.values():
        ai = cat_data.get("ai_report", {})
        cat_words: set[str] = set()
        for theme in ai.get("key_themes", []):
            cat_words.update(theme.lower().split())
        cat_words.update(ai.get("summary", "").lower().split())

        overlap = len(tweet_words & cat_words)
        if overlap > best_score:
            best_score = overlap
            best_cat = cat_data

    return best_cat


def _load_quoted_ids(path: Path) -> Dict[str, str]:
    """Load quoted tweet IDs. Returns {tweet_id: iso_timestamp}."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, ValueError):
        return {}


def _save_quoted_ids(path: Path, quoted: Dict[str, str]) -> None:
    """Save quoted tweet IDs, pruning entries older than retention window."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=QUOTED_TWEETS_RETENTION_DAYS)
    pruned: Dict[str, str] = {}
    for tid, ts in quoted.items():
        try:
            if datetime.fromisoformat(ts) > cutoff:
                pruned[tid] = ts
        except (ValueError, TypeError):
            pass  # Drop malformed entries
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pruned, indent=2) + "\n", encoding="utf-8")


def _search_tweets(client: Any, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """Search recent tweets using X API v2."""
    try:
        # Ensure max_results is within API bounds (10-100)
        clamped = max(10, min(max_results, 100))
        response = client.search_recent_tweets(
            query=f"{query} -is:retweet -is:reply lang:en",
            max_results=clamped,
            tweet_fields=["created_at", "public_metrics", "author_id"],
            expansions=["author_id"],
            user_fields=["username"],
        )
        if not response.data:
            return []

        # Build author lookup
        includes = response.includes or {}
        user_list = includes.get("users") or []
        users = {u.id: u.username for u in user_list}

        tweets = []
        for tweet in response.data:
            metrics = tweet.public_metrics or {}
            tweets.append({
                "id": str(tweet.id),
                "text": tweet.text,
                "author_id": str(tweet.author_id),
                "author_username": users.get(tweet.author_id, "unknown"),
                "created_at": tweet.created_at.isoformat() if tweet.created_at else "",
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
            })
        return tweets
    except Exception as e:
        print(f"[search] Error for '{query}': {type(e).__name__}: {e}", file=sys.stderr)
        return []


def _filter_and_score(
    tweets: List[Dict[str, Any]],
    quoted_ids: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Filter by engagement/recency/content, score, and rank."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_TWEET_AGE_HOURS)
    candidates = []

    for tw in tweets:
        # Skip self
        if tw.get("author_username", "").lower() == SELF_USERNAME.lower():
            continue

        # Skip already quoted
        if tw["id"] in quoted_ids:
            continue

        # Engagement minimum (must meet BOTH thresholds for popular tweets)
        likes = tw.get("likes", 0)
        retweets = tw.get("retweets", 0)
        if likes < MIN_LIKES or retweets < MIN_RETWEETS:
            continue

        # Recency check
        created = tw.get("created_at", "")
        if created:
            try:
                tweet_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if tweet_time < cutoff:
                    continue
            except (ValueError, TypeError):
                pass

        # Profanity filter
        if _has_profanity(tw.get("text", "")):
            continue

        tw["score"] = likes + (retweets * 2)
        candidates.append(tw)

    candidates.sort(key=lambda t: t["score"], reverse=True)
    return candidates[:MAX_QUOTES_PER_RUN]


def main() -> int:
    dry_run = os.getenv("X_DRY_RUN", "").strip().lower() == "true"
    if dry_run:
        print("[DRY RUN MODE] No tweets will be posted.\n")

    # ── Load today's report ──
    date_key = _today_key()
    site_root = Path(__file__).resolve().parents[1]
    report = _load_report(site_root, date_key)
    if report is None:
        return 1

    # ── Extract search terms ──
    search_terms = _extract_search_terms(report)
    if not search_terms:
        print("No search terms extracted from report.")
        return 0
    print(f"Search terms ({len(search_terms)}): {', '.join(search_terms)}")

    # ── Validate credentials ──
    bearer_token = os.getenv("X_BEARER_TOKEN", "").strip()
    consumer_key = os.getenv("X_CONSUMER_KEY", "").strip()
    consumer_secret = os.getenv("X_CONSUMER_SECRET", "").strip()
    access_token = os.getenv("X_ACCESS_TOKEN", "").strip()
    access_secret = os.getenv("X_ACCESS_SECRET", "").strip()

    if not bearer_token:
        print("ERROR: X_BEARER_TOKEN required for search.", file=sys.stderr)
        return 1
    if not all([consumer_key, consumer_secret, access_token, access_secret]):
        print("ERROR: Missing X API OAuth credentials.", file=sys.stderr)
        return 1

    # ── Setup clients ──
    import tweepy

    search_client = tweepy.Client(bearer_token=bearer_token)
    post_client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    openai_client = None
    if openai_key:
        import openai
        openai_client = openai.OpenAI(api_key=openai_key)

    if openai_client is None:
        print("ERROR: OPENAI_API_KEY required for commentary generation.", file=sys.stderr)
        return 1

    reply_agent = ReplyWriterAgent(client=openai_client, model=openai_model)

    # ── Load quote history ──
    quoted_path = site_root / "news" / "data" / "replied_tweets.json"
    quoted_ids = _load_quoted_ids(quoted_path)
    print(f"Quote history: {len(quoted_ids)} tweets in log")

    # ── Search for candidate tweets ──
    all_tweets: Dict[str, Dict[str, Any]] = {}
    for term in search_terms:
        results = _search_tweets(search_client, term, max_results=20)
        for tw in results:
            if tw["id"] not in all_tweets:
                all_tweets[tw["id"]] = tw
        print(f"  '{term}': {len(results)} results ({len(all_tweets)} total unique)")

    if not all_tweets:
        print("\nNo tweets found matching search terms.")
        _save_quoted_ids(quoted_path, quoted_ids)
        return 0

    # ── Filter and score ──
    candidates = _filter_and_score(list(all_tweets.values()), quoted_ids)
    print(f"\nFiltered to {len(candidates)} candidates (max {MAX_QUOTES_PER_RUN})")

    if not candidates:
        print("No candidates passed filters.")
        _save_quoted_ids(quoted_path, quoted_ids)
        return 0

    # ── Generate and post quote tweets ──
    quotes_posted = 0
    for i, tw in enumerate(candidates):
        print(f"\n--- Candidate {i + 1}/{len(candidates)} "
              f"(score: {tw['score']}, likes: {tw['likes']}, RTs: {tw['retweets']}) ---")
        print(f"@{tw['author_username']}: {tw['text'][:140]}...")

        # Match to most relevant category
        cat_context = _match_category(tw["text"], report)
        if cat_context is None:
            categories = report.get("categories", {})
            if categories:
                cat_context = next(iter(categories.values()))
            else:
                print("  Skipped: no category data available")
                continue

        # Generate commentary
        commentary = reply_agent.run(
            tweet_text=tw["text"],
            category_context=cat_context,
        )

        if commentary is None:
            print("  Skipped: commentary generation failed or was rejected")
            continue

        print(f"  Commentary ({len(commentary)} chars): {commentary}")

        if dry_run:
            print("  [DRY RUN] Would quote tweet — not posted.")
            quoted_ids[tw["id"]] = datetime.now(timezone.utc).isoformat()
            quotes_posted += 1
        else:
            try:
                response = post_client.create_tweet(
                    text=commentary,
                    quote_tweet_id=tw["id"],
                )
                new_tweet_id = response.data["id"]
                print(f"  Posted: https://x.com/tldrnewsusa/status/{new_tweet_id}")
                quoted_ids[tw["id"]] = datetime.now(timezone.utc).isoformat()
                quotes_posted += 1
            except tweepy.Forbidden as e:
                err_msg = str(e).lower()
                if "duplicate" in err_msg:
                    print("  Skipped: duplicate content (already quoted)")
                    quoted_ids[tw["id"]] = datetime.now(timezone.utc).isoformat()
                else:
                    print(f"  ERROR (Forbidden): {e}", file=sys.stderr)
            except tweepy.TooManyRequests as e:
                print(f"  Rate limited. Stopping. {e}", file=sys.stderr)
                break
            except Exception as e:
                print(f"  ERROR: {type(e).__name__}: {e}", file=sys.stderr)

        # Delay between posts (skip after last)
        if i < len(candidates) - 1 and quotes_posted < MAX_QUOTES_PER_RUN:
            print(f"  Waiting {QUOTE_DELAY_SECONDS}s...")
            time.sleep(QUOTE_DELAY_SECONDS)

    # ── Save history ──
    _save_quoted_ids(quoted_path, quoted_ids)
    print(f"\nDone. Posted {quotes_posted} quote tweets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
