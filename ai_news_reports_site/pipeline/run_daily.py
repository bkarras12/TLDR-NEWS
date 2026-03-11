from __future__ import annotations

import os
import re
import sys
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Set

from openai import OpenAI

from pipeline.config import CATEGORIES
from pipeline.agents.rss_reader import RssReaderAgent
from pipeline.agents.curator import CuratorAgent
from pipeline.agents.sentiment import SentimentAgent
from pipeline.agents.report_writer import ReportWriterAgent
from pipeline.agents.publisher import PublisherAgent
from pipeline.agents.base import NewsItem, SentimentResult
from pipeline.agents.tweet_writer import TweetWriterAgent
from pipeline.agents.article_writer import ArticleWriterAgent


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


STOP_WORDS: Set[str] = {
    # Articles, pronouns, determiners
    "the", "a", "an", "this", "that", "these", "those", "it", "its",
    "you", "your", "yours", "he", "him", "his", "she", "her", "hers",
    "we", "our", "ours", "they", "them", "their", "theirs", "me", "my",
    # Be / have / do
    "is", "are", "was", "were", "be", "been", "being", "am",
    "have", "has", "had", "do", "does", "did", "done",
    # Modals
    "will", "would", "could", "should", "may", "might", "shall", "can",
    "need", "dare", "ought", "must",
    # Prepositions / conjunctions
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "about", "around",
    "and", "but", "or", "nor", "not", "so", "yet", "both",
    "either", "neither",
    # Adverbs / adjectives / filler
    "again", "further", "then", "once", "each", "every", "all", "any",
    "few", "more", "most", "other", "some", "such", "no", "only", "own",
    "same", "than", "too", "very", "just", "because", "if", "when",
    "while", "how", "what", "which", "who", "whom", "also", "still",
    "even", "back", "now", "here", "there", "where", "why",
    # Common news filler words
    "new", "says", "said", "say", "tell", "tells", "told", "ask", "asks",
    "first", "last", "many", "much", "up", "get", "gets", "got",
    "make", "makes", "made", "take", "takes", "took", "come", "comes",
    "came", "going", "goes", "went", "gone", "want", "wants", "wanted",
    "know", "knows", "knew", "think", "thinks", "see", "seen", "look",
    "looks", "give", "gives", "use", "used", "find", "found",
    "put", "set", "run", "let", "keep", "keeps", "show", "shows",
    "try", "call", "calls", "called", "big", "old", "long", "way",
    "day", "days", "year", "years", "time", "week", "weeks", "month",
    "part", "good", "bad", "best", "worst", "real", "really",
    "right", "left", "high", "low", "top", "end", "two", "three",
    "one", "people", "world", "life", "man", "men", "woman", "women",
    "thing", "things", "well", "down", "like", "over", "after", "don",
    "won", "being", "help", "helps", "report", "reports", "according",
    "near", "per", "via", "ahead", "amid", "among",
}

# Minimum word length to be considered a keyword
_MIN_KEYWORD_LEN = 4


def _extract_keywords(title: str) -> Set[str]:
    """Extract meaningful keywords from a headline."""
    words = re.sub(r"[^a-z0-9\s]", "", title.lower()).split()
    return {w for w in words if len(w) >= _MIN_KEYWORD_LEN and w not in STOP_WORDS}


def _find_trending_topics(categories_out: Dict[str, Any]) -> List[str]:
    """Find topics mentioned across multiple category feeds."""
    # Map keyword → set of categories it appears in
    keyword_cats: Dict[str, Set[str]] = {}
    keyword_titles: Dict[str, List[str]] = {}

    for cat_key, cat_data in categories_out.items():
        for item in cat_data.get("items", []):
            title = item.get("title", "")
            keywords = _extract_keywords(title)
            for kw in keywords:
                keyword_cats.setdefault(kw, set()).add(cat_key)
                keyword_titles.setdefault(kw, []).append(title)

    # Find keywords appearing in 2+ categories with 3+ total mentions
    cross_keywords = {
        kw for kw, cats in keyword_cats.items()
        if len(cats) >= 2 and len(keyword_titles[kw]) >= 3
    }

    if not cross_keywords:
        # Fallback: 2+ categories, 2+ mentions
        cross_keywords = {
            kw for kw, cats in keyword_cats.items()
            if len(cats) >= 2 and len(keyword_titles[kw]) >= 2
        }

    if not cross_keywords:
        return []

    # Score by number of categories × number of mentions
    scored = []
    for kw in cross_keywords:
        score = len(keyword_cats[kw]) * len(keyword_titles[kw])
        scored.append((score, kw))
    scored.sort(reverse=True)

    return [kw for _, kw in scored[:10]]


def main() -> int:
    site_root = Path(__file__).resolve().parents[1]
    date_key = local_date_key()

    # Normalize env vars (GitHub Secrets frequently include trailing newlines).
    model = (os.getenv("OPENAI_MODEL") or "").strip() or "gpt-4o-mini"
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip() or None
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
            # This should be rare now (writer has its own robust fallbacks),
            # but we keep this guard so the pipeline never crashes.
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

    # Generate tweet text for each category
    tweet_writer = TweetWriterAgent(client=client, model=model)
    for key, cat_data in categories_out.items():
        cat_items = [
            NewsItem(
                title=it["title"],
                url=it["url"],
                published=it.get("published"),
                summary=it.get("summary"),
                source=it.get("source"),
            )
            for it in cat_data.get("items", [])
        ]
        cat_sentiment = SentimentResult(
            score=cat_data["sentiment"]["score"],
            label=cat_data["sentiment"]["label"],
            rationale=cat_data["sentiment"]["rationale"],
        )
        tweet = tweet_writer.run(
            category_key=key,
            category_title=cat_data["title"],
            items=cat_items,
            sentiment=cat_sentiment,
        )
        if tweet:
            cat_data["tweet_text"] = tweet
            print(f"[{key}] Tweet: {tweet[:80]}...")

    # Detect trending topics across categories
    trending = _find_trending_topics(categories_out)
    if trending:
        print(f"Trending topics across categories: {', '.join(trending[:5])}")

    daily_report = {
        "date": date_key,
        "generated_at_utc": iso_utc_now(),
        "timezone": TZ,
        "model": model,
        "trending_topics": trending,
        "categories": categories_out,
    }

    publisher = PublisherAgent(site_root=site_root)
    out_path = publisher.write_daily_report(date_key, daily_report)
    publisher.update_index(date_key=date_key, available_categories=list(CATEGORIES.keys()))

    # GEO: Static HTML pages, sitemap, RSS feeds, category landing pages
    static_pages = publisher.write_static_pages(date_key, daily_report)
    print(f"Wrote {len(static_pages)} static HTML pages")

    landing_pages = publisher.write_category_landing_pages(date_key, daily_report)
    print(f"Wrote {len(landing_pages)} category landing pages")

    sitemap_path = publisher.write_sitemap(base_url="https://tldrnews.info/")
    print(f"Wrote sitemap: {sitemap_path}")

    feeds = publisher.write_rss_feeds(date_key, daily_report, base_url="https://tldrnews.info/")
    print(f"Wrote {len(feeds)} RSS feeds")

    # Generate daily roundup article
    article_writer = ArticleWriterAgent(client=client, model=model)
    article_path = article_writer.write_article(
        site_root=site_root,
        date_key=date_key,
        daily_report=daily_report,
    )
    if article_path:
        print(f"Wrote article: {article_path}")
    else:
        print("Skipped article generation (no client or generation failed)")

    # Generate static HTML for all articles
    article_pages = publisher.write_article_pages()
    print(f"Wrote {len(article_pages)} static article HTML pages")

    print(f"Saved daily report to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
