from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any

_STOP = {
    "the", "a", "an", "of", "in", "to", "and", "for", "on", "is", "are",
    "at", "by", "with", "its", "as", "this", "that", "it", "from", "or",
    "be", "has", "was", "are", "were", "been", "have", "had",
}


def _words(text: str) -> set:
    return {w.lower().strip(".,;:") for w in text.split()
            if w.lower().strip(".,;:") not in _STOP and len(w) > 2}


def _match(a: str, b: str) -> bool:
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return False
    return len(wa & wb) / min(len(wa), len(wb)) >= 0.5


class TrendTrackerAgent:
    """
    Reads the last `lookback` daily report JSONs and identifies key_themes that
    recur across multiple days within each category.

    Returns a dict: { category_key: [{"theme": str, "streak": int}, ...] }
    Only themes appearing in 2+ of the lookback reports are included.
    """

    def __init__(self, reports_dir: Path, lookback: int = 7):
        self.reports_dir = reports_dir
        self.lookback = lookback

    def run(self, today_date: str, categories: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        past_reports = self._load_past(today_date)
        if not past_reports:
            return {}

        result: Dict[str, List[Dict[str, Any]]] = {}
        for cat in categories:
            history: List[List[str]] = []
            for report in past_reports:
                themes = (
                    report.get("categories", {})
                          .get(cat, {})
                          .get("ai_report", {})
                          .get("key_themes", [])
                )
                history.append([t for t in themes if isinstance(t, str)])

            # Count recurrence across days using fuzzy word-overlap matching
            seen: List[Dict[str, Any]] = []
            for day_themes in history:
                for theme in day_themes:
                    matched = False
                    for entry in seen:
                        if _match(theme, entry["theme"]):
                            entry["streak"] += 1
                            matched = True
                            break
                    if not matched:
                        seen.append({"theme": theme, "streak": 1})

            trending = [e for e in seen if e["streak"] >= 2]
            trending.sort(key=lambda x: -x["streak"])
            if trending:
                result[cat] = trending[:5]

        return result

    def _load_past(self, today: str) -> List[Dict[str, Any]]:
        paths = sorted(self.reports_dir.glob("*.json"), reverse=True)
        out: List[Dict[str, Any]] = []
        for p in paths:
            if p.stem == today:
                continue
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                pass
            if len(out) >= self.lookback:
                break
        return out
