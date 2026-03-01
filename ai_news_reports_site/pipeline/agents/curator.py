from __future__ import annotations

import re
from typing import List

from .base import NewsItem


class CuratorAgent:
    def __init__(self, max_items: int = 12):
        self.max_items = max_items

    @staticmethod
    def _norm(s: str) -> str:
        s = s.lower().strip()
        s = re.sub(r"\s+", " ", s)
        s = re.sub(r"[^a-z0-9\s]", "", s)
        return s

    def run(self, items: List[NewsItem]) -> List[NewsItem]:
        seen = set()
        curated: List[NewsItem] = []

        for it in items:
            key = self._norm(it.title)[:120]
            if key in seen:
                continue
            seen.add(key)

            # minor cleanup
            if it.summary:
                it.summary = it.summary.strip()

            curated.append(it)
            if len(curated) >= self.max_items:
                break

        return curated
