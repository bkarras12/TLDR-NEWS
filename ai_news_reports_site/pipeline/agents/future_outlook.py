from __future__ import annotations

import json
from typing import Any, Dict, List

from openai import OpenAI

from .base import NewsItem, SentimentResult


OUTLOOK_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "next_24_72_hours": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 6},
        "next_1_4_weeks": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 6},
        "watch_list": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 10},
        "confidence": {"type": "string", "enum": ["Low", "Medium", "High"]},
    },
    "required": ["next_24_72_hours", "next_1_4_weeks", "watch_list", "confidence"],
}


class FutureOutlookAgent:
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    @staticmethod
    def _items_to_prompt(items: List[NewsItem]) -> str:
        lines = []
        for i, it in enumerate(items, 1):
            lines.append(f"{i}. {it.title}")
            if it.summary:
                lines.append(f"   - Summary: {it.summary}")
            lines.append(f"   - Link: {it.url}")
        return "\n".join(lines)

    def run(
        self,
        *,
        category_title: str,
        source_name: str,
        items: List[NewsItem],
        sentiment: SentimentResult,
    ) -> Dict[str, Any]:
        if not items:
            return {
                "next_24_72_hours": ["Check back when the feed is available."],
                "next_1_4_weeks": ["Check back when the feed is available."],
                "watch_list": ["Feed availability"],
                "confidence": "Low",
            }

        prompt = f"""Create a future outlook for today's {category_title} report.

SOURCE: {source_name}
SENTIMENT:
- label: {sentiment.label}
- score: {sentiment.score:.3f}
- note: {sentiment.rationale}

HEADLINES:
{self._items_to_prompt(items)}

Return JSON only that matches the schema.
Ground every point in the supplied headlines/summaries and avoid speculation beyond reasonable scenarios.
"""

        try:
            resp = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "developer",
                        "content": "You are a risk analyst producing cautious outlooks from current headlines.",
                    },
                    {"role": "user", "content": prompt},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "future_outlook",
                        "schema": OUTLOOK_SCHEMA,
                        "strict": True,
                    }
                },
            )
            raw = resp.output_text
        except Exception:
            resp = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "developer",
                        "content": "You are a risk analyst producing cautious outlooks from current headlines.",
                    },
                    {"role": "user", "content": prompt + "\n\n(Use valid JSON.)"},
                ],
                text={"format": {"type": "json_object"}},
            )
            raw = resp.output_text

        try:
            data = json.loads(raw)
        except Exception:
            data = {
                "next_24_72_hours": ["Outlook generation returned invalid JSON; review current headlines."],
                "next_1_4_weeks": ["Outlook generation returned invalid JSON; review current headlines."],
                "watch_list": ["Model output reliability", "Major developing stories", "Source updates"],
                "confidence": "Low",
            }

        return data
