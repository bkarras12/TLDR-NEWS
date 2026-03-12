"""Search X for trending news conversations and post AI-generated replies.

Usage:
    python -m pipeline.post_replies

Environment variables:
    X_CONSUMER_KEY     - OAuth 1.0a consumer key
    X_CONSUMER_SECRET  - OAuth 1.0a consumer secret
    X_ACCESS_TOKEN     - OAuth 1.0a access token
    X_ACCESS_SECRET    - OAuth 1.0a access token secret
    X_BEARER_TOKEN     - OAuth 2.0 bearer token (for search)
    OPENAI_API_KEY     - OpenAI API key (for reply generation)
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
MAX_REPLIES_PER_RUN = 10
MIN_LIKES = 5
MIN_RETWEETS = 3
MAX_TWEET_AGE_HOURS = 6
REPLY_DELAY_SECONDS = 60
REPLIED_TWEETS_RETENTION_DAYS = 7
SELF_USERNAME = "tldrnewsusa"
TZ = "America/Denver"

# Basic profanity filter for inbound tweets
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
        print(f"No report found for {date_key} at {report_path}", file=sys.stderr)
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
            # Extract capitalized proper nouns (2+ words) as search terms
            proper_nouns = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", headline)
            for noun in proper_nouns[:2]:
                if noun not in terms:
                    terms.append(noun)

    # Deduplicate while preserving order
    seen = set()
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
        themes = ai.get("key_themes", [])
        summary = ai.get("summary", "")

        # Score by keyword overlap with themes + summary
        cat_words = set()
        for theme in themes:
            cat_words.update(theme.lower().split())
        cat_words.update(summary.lower().split())

        overlap = len(tweet_words & cat_words)
        if overlap > best_score:
            best_score = overlap
            best_cat = cat_data

    return best_cat


def _load_replied_ids(path: Path) -> Dict[str, str]:
    """Load replied tweet IDs. Returns {tweet_id: iso_timestamp}."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {}


def _save_replied_ids(path: Path, replied: Dict[str, str]) -> None:
    """Save replied tweet IDs, pruning entries older than retention window."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=REPLIED_TWEETS_RETENTION_DAYS)
    pruned = {
        tid: ts for tid, ts in replied.items()
        if datetime.fromisoformat(ts) > cutoff
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pruned, indent=2) + "\n", encoding="utf-8")


def _search_tweets(client: Any, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """Search recent tweets using X API v2. Returns list of tweet dicts."""
    try:
        response = client.search_recent_tweets(
            query=f"{query} -is:retweet -is:reply lang:en",
            max_results=min(max_results, 100),
            tweet_fields=["created_at", "public_metrics", "author_id", "in_reply_to_user_id"],
            expansions=["author_id"],
            user_fields=["username"],
        )
        if not response.data:
            return []

        # Build author lookup
        users = {u.id: u.username for u in (response.includes.get("users", []) or [])}

        tweets = []
        for tweet in response.data:
            metrics = tweet.public_metrics or {}
            tweets.append({
                "id": str(tweet.id),
                "text": tweet.text,
                "author_id": str(tweet.author_id),
                "author_username": users.get(tweet.author_id, ""),
                "created_at": tweet.created_at.isoformat() if tweet.created_at else "",
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
                "is_reply": tweet.in_reply_to_user_id is not None,
            })
        return tweets
    except Exception as e:
        print(f"[search] Error searching for '{query}': {type(e).__name__}: {e}", file=sys.stderr)
        return []


def _filter_and_score(
    tweets: List[Dict[str, Any]],
    replied_ids: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Filter tweets by engagement/recency/content, then score and rank."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_TWEET_AGE_HOURS)
    candidates = []

    for tw in tweets:
        # Skip replies
        if tw.get("is_reply"):
            continue

        # Skip self
        if tw.get("author_username", "").lower() == SELF_USERNAME.lower():
            continue

        # Skip already replied
        if tw["id"] in replied_ids:
            continue

        # Engagement minimum
        likes = tw.get("likes", 0)
        retweets = tw.get("retweets", 0)
        if likes < MIN_LIKES and retweets < MIN_RETWEETS:
            continue

        # Recency check
        created = tw.get("created_at", "")
        if created:
            try:
                tweet_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if tweet_time < cutoff:
                    continue
            except ValueError:
                pass

        # Profanity filter
        if _has_profanity(tw.get("text", "")):
            continue

        # Score: likes + 2*retweets
        tw["score"] = likes + (retweets * 2)
        candidates.append(tw)

    # Sort by score descending
    candidates.sort(key=lambda t: t["score"], reverse=True)
    return candidates[:MAX_REPLIES_PER_RUN]


def main() -> int:
    dry_run = os.getenv("X_DRY_RUN", "").strip().lower() == "true"

    # Load report
    date_key = _today_key()
    site_root = Path(__file__).resolve().parents[1]
    report = _load_report(site_root, date_key)
    if report is None:
        return 1

    # Extract search terms
    search_terms = _extract_search_terms(report)
    if not search_terms:
        print("No search terms extracted from report.", file=sys.stderr)
        return 0

    print(f"Search terms ({len(search_terms)}): {', '.join(search_terms)}")

    # Setup X client (bearer token for search)
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

    import tweepy

    # Read client (bearer token) for searching
    search_client = tweepy.Client(bearer_token=bearer_token)

    # Write client (OAuth 1.0a) for posting replies
    post_client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )

    # Setup OpenAI client for reply generation
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    openai_client = None
    if openai_key:
        import openai
        openai_client = openai.OpenAI(api_key=openai_key)

    reply_agent = ReplyWriterAgent(client=openai_client, model=openai_model)

    # Load reply history
    replied_path = site_root / "news" / "data" / "replied_tweets.json"
    replied_ids = _load_replied_ids(replied_path)
    print(f"Reply history: {len(replied_ids)} tweets in log")

    # Search for candidate tweets
    all_tweets: Dict[str, Dict[str, Any]] = {}  # dedup by tweet ID
    for term in search_terms:
        results = _search_tweets(search_client, term, max_results=20)
        for tw in results:
            if tw["id"] not in all_tweets:
                all_tweets[tw["id"]] = tw
        print(f"  Searched '{term}': {len(results)} results ({len(all_tweets)} total unique)")

    if not all_tweets:
        print("No tweets found matching search terms.")
        _save_replied_ids(replied_path, replied_ids)
        return 0

    # Filter and score
    candidates = _filter_and_score(list(all_tweets.values()), replied_ids)
    print(f"\nFiltered to {len(candidates)} candidates (max {MAX_REPLIES_PER_RUN})")

    if not candidates:
        print("No candidates passed filters.")
        _save_replied_ids(replied_path, replied_ids)
        return 0

    # Generate and post replies
    replies_posted = 0
    for i, tw in enumerate(candidates):
        print(f"\n--- Candidate {i + 1}/{len(candidates)} (score: {tw['score']}) ---")
        print(f"@{tw['author_username']}: {tw['text'][:120]}...")

        # Match to most relevant category
        cat_context = _match_category(tw["text"], report)
        if cat_context is None:
            print("  Skipped: no matching category")
            continue

        # Generate reply
        reply_text = reply_agent.run(
            tweet_text=tw["text"],
            category_context=cat_context,
        )

        if reply_text is None:
            print("  Skipped: reply generation failed or was rejected")
            continue

        print(f"  Reply ({len(reply_text)} chars): {reply_text}")

        if dry_run:
            print("  [DRY RUN] Not posted.")
            replied_ids[tw["id"]] = datetime.now(timezone.utc).isoformat()
            replies_posted += 1
        else:
            try:
                response = post_client.create_tweet(
                    text=reply_text,
                    in_reply_to_tweet_id=tw["id"],
                )
                reply_id = response.data["id"]
                print(f"  Posted: https://x.com/tldrnewsusa/status/{reply_id}")
                replied_ids[tw["id"]] = datetime.now(timezone.utc).isoformat()
                replies_posted += 1
            except Exception as e:
                print(f"  ERROR posting reply: {type(e).__name__}: {e}", file=sys.stderr)

        # Rate limit delay (skip after last reply)
        if i < len(candidates) - 1 and replies_posted < MAX_REPLIES_PER_RUN:
            print(f"  Waiting {REPLY_DELAY_SECONDS}s...")
            time.sleep(REPLY_DELAY_SECONDS)

    # Save reply history
    _save_replied_ids(replied_path, replied_ids)
    print(f"\nDone. Posted {replies_posted} replies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
