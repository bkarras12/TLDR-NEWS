from __future__ import annotations

import time
from typing import List, Optional

import feedparser
import requests

from .base import NewsItem


class RssReaderAgent:
    def __init__(self, feed_url: str, source_name: str, timeout_s: int = 20):
        self.feed_url = feed_url
        self.source_name = source_name
        self.timeout_s = timeout_s

    def _fetch(self) -> str:
        # Some publishers block default user agents; a simple UA helps reliability.
        headers = {
            "User-Agent": "ai-news-reports-bot/1.0 (+https://github.com/)",
            "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        }
        r = requests.get(self.feed_url, headers=headers, timeout=self.timeout_s)
        r.raise_for_status()
        return r.text

    def run(self, limit: int = 12) -> List[NewsItem]:
        xml = self._fetch()
        feed = feedparser.parse(xml)

        items: List[NewsItem] = []
        for e in feed.entries[: max(0, limit * 2)]:  # pull extra; curator will trim
            title = (getattr(e, "title", "") or "").strip()
            link = (getattr(e, "link", "") or "").strip()
            if not title or not link:
                continue

            published = (getattr(e, "published", None) or getattr(e, "updated", None) or None)
            summary = (getattr(e, "summary", None) or getattr(e, "description", None) or None)
            if summary:
                summary = " ".join(summary.split())
                # Keep LLM inputs smaller
                summary = summary[:500]

            items.append(
                NewsItem(
                    title=title,
                    url=link,
                    published=published,
                    summary=summary,
                    source=self.source_name,
                )
            )

        # polite delay (helps if you add more feeds later)
        time.sleep(0.5)
        return items
