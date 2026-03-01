from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class NewsItem:
    title: str
    url: str
    published: Optional[str] = None
    summary: Optional[str] = None
    source: Optional[str] = None


@dataclass
class SentimentResult:
    score: float  # [-1, 1]
    label: str    # Positive / Neutral / Negative / Mixed
    rationale: str
