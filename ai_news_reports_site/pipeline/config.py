from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class CategoryConfig:
    key: str
    title: str
    site_name: str
    site_url: str
    feed_url: str
    max_items: int = 12


# 5 different news websites (RSS)
CATEGORIES: Dict[str, CategoryConfig] = {
    "world": CategoryConfig(
        key="world",
        title="World",
        site_name="BBC News",
        site_url="https://www.bbc.com/news",
        feed_url="https://feeds.bbci.co.uk/news/world/rss.xml",
        max_items=12,
    ),
    "business": CategoryConfig(
        key="business",
        title="Business",
        site_name="The Guardian",
        site_url="https://www.theguardian.com/business",
        feed_url="https://www.theguardian.com/business/rss",
        max_items=12,
    ),
    "technology": CategoryConfig(
        key="technology",
        title="Technology",
        site_name="The Verge",
        site_url="https://www.theverge.com",
        feed_url="https://www.theverge.com/rss/index.xml",
        max_items=12,
    ),
    "sports": CategoryConfig(
        key="sports",
        title="Sports",
        site_name="ESPN",
        site_url="https://www.espn.com",
        feed_url="https://www.espn.com/espn/rss/news",
        max_items=12,
    ),
    "science": CategoryConfig(
        key="science",
        title="Science",
        site_name="ScienceDaily",
        site_url="https://www.sciencedaily.com",
        feed_url="https://www.sciencedaily.com/rss/top/science.xml",
        max_items=12,
    ),
}
