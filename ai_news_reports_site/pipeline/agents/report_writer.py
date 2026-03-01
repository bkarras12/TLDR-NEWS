from __future__ import annotations

import json
from typing import Any, Dict, List

from openai import OpenAI

from .base import NewsItem, SentimentResult


REPORT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "key_themes": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 8},
        "notable_headlines": {
            "type": "array",
            "minItems": 5,
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "headline": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                    "signal": {"type": "string", "enum": ["Opportunity", "Risk", "Unclear"]},
                },
                "required": ["headline", "why_it_matters", "signal"],
            },
        },
        "future_outlook": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "next_24_72_hours": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 6},
                "next_1_4_weeks": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 6},
                "watch_list": {"type": "array", "items": {"type": "string"}, "minItems": 4, "maxItems": 10},
                "confidence": {"type": "string", "enum": ["Low", "Medium", "High"]},
            },
            "required": ["next_24_72_hours", "next_1_4_weeks", "watch_list", "confidence"],
        },
        "caveats": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 5},
    },
    "required": ["summary", "key_themes", "notable_headlines", "future_outlook", "caveats"],
}


class ReportWriterAgent:
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model

    @staticmethod
    def _items_to_prompt(items: List[NewsItem]) -> str:
        lines = []
        for i, it in enumerate(items, 1):
            lines.append(f"{i}. {it.title}")
            if it.published:
                lines.append(f"   - Published: {it.published}")
            lines.append(f"   - Link: {it.url}")
            if it.summary:
                lines.append(f"   - Summary: {it.summary}")
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
                "summary": "No headlines were available from the RSS feed at generation time.",
                "key_themes": ["Feed unavailable", "No headlines", "Try again later"],
                "notable_headlines": [],
                "future_outlook": {
                    "next_24_72_hours": ["Check back when the feed is available."],
                    "next_1_4_weeks": ["Check back when the feed is available."],
                    "watch_list": ["Feed availability"],
                    "confidence": "Low",
                },
                "caveats": [
                    "RSS feed returned no usable items.",
                    "This is an automated report; verify details via the source links.",
                ],
            }

        headlines_blob = self._items_to_prompt(items)

        developer_instructions = (
            "You are an expert news editor. Your job is to write a comprehensive, easy-to-scan daily report "
            "based ONLY on the provided RSS headlines and summaries. Do not invent facts. If something is unclear, "
            "say so. Write neutral, professional analysis."
        )

        user_prompt = f"""Create today's report for the category: {category_title}.

SOURCE: {source_name}
SENTIMENT_SIGNAL:
- label: {sentiment.label}
- score: {sentiment.score:.3f}
- note: {sentiment.rationale}

HEADLINES (title, date if present, link, short summary):
{headlines_blob}

Return JSON ONLY that matches the provided schema.
"""

        # Responses API uses text.format for structured outputs.
        # We try json_schema first; if it fails for any reason, fall back to json_object.
        try:
            resp = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "developer", "content": developer_instructions},
                    {"role": "user", "content": user_prompt},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "daily_news_report",
                        "schema": REPORT_SCHEMA,
                        "strict": True,
                    }
                },
            )
            raw = resp.output_text
        except Exception:
            resp = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "developer", "content": developer_instructions},
                    {"role": "user", "content": user_prompt + "\n\n(Use valid JSON.)"},
                ],
                text={"format": {"type": "json_object"}},
            )
            raw = resp.output_text

        try:
            data = json.loads(raw)
        except Exception as e:
            # last resort: wrap as minimal structure
            data = {
                "summary": raw.strip()[:2000],
                "key_themes": ["Parsing error", "Raw model output used", "Verify via links"],
                "notable_headlines": [],
                "future_outlook": {
                    "next_24_72_hours": ["Model output could not be parsed; see summary."],
                    "next_1_4_weeks": ["Model output could not be parsed; see summary."],
                    "watch_list": ["Parsing reliability", "Feed stability"],
                    "confidence": "Low",
                },
                "caveats": [
                    f"Model output could not be parsed as JSON: {type(e).__name__}.",
                    "This is an automated report; verify details via the source links.",
                ],
            }

        return data
