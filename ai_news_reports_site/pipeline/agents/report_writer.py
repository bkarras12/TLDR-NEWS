from __future__ import annotations

import json
from typing import Any, Dict, List

from openai import OpenAI

from .base import NewsItem, SentimentResult
from .executive_summary import ExecutiveSummaryAgent
from .future_outlook import FutureOutlookAgent


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
    def __init__(self, client: OpenAI | None, model: str):
        self.client = client
        self.model = model
        self.executive_summary_agent = (
            ExecutiveSummaryAgent(client=client, model=model) if client else None
        )
        self.future_outlook_agent = FutureOutlookAgent(client=client, model=model) if client else None

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

        if self.client is None:
            return self._build_local_report(items=items, sentiment=sentiment)

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

        data = self._fill_summary_and_outlook(
            data=data,
            category_title=category_title,
            source_name=source_name,
            items=items,
            sentiment=sentiment,
        )

        return data

    @staticmethod
    def _is_missing_or_failed_text(value: Any) -> bool:
        if not isinstance(value, str):
            return True
        text = value.strip().lower()
        return (not text) or ("failed" in text)


    @classmethod
    def _is_missing_or_failed_outlook(cls, value: Any) -> bool:
        if not isinstance(value, dict):
            return True

        required_keys = ["next_24_72_hours", "next_1_4_weeks", "watch_list", "confidence"]
        if any(k not in value for k in required_keys):
            return True

        for key in ["next_24_72_hours", "next_1_4_weeks", "watch_list"]:
            entries = value.get(key)
            if not isinstance(entries, list) or not entries:
                return True
            for entry in entries:
                if cls._is_missing_or_failed_text(entry):
                    return True

        conf = value.get("confidence")
        if conf not in {"Low", "Medium", "High"}:
            return True

        return False

    def _fill_summary_and_outlook(
        self,
        *,
        data: Dict[str, Any],
        category_title: str,
        source_name: str,
        items: List[NewsItem],
        sentiment: SentimentResult,
    ) -> Dict[str, Any]:
        summary_missing = self._is_missing_or_failed_text(data.get("summary"))
        outlook_missing = self._is_missing_or_failed_outlook(data.get("future_outlook"))

        if summary_missing and self.executive_summary_agent:
            try:
                data["summary"] = self.executive_summary_agent.run(
                    category_title=category_title,
                    source_name=source_name,
                    items=items,
                    sentiment=sentiment,
                )
            except Exception:
                pass

        if outlook_missing and self.future_outlook_agent:
            try:
                data["future_outlook"] = self.future_outlook_agent.run(
                    category_title=category_title,
                    source_name=source_name,
                    items=items,
                    sentiment=sentiment,
                )
            except Exception:
                pass

        return data

    @staticmethod
    def _build_local_report(*, items: List[NewsItem], sentiment: SentimentResult) -> Dict[str, Any]:
        top_titles = [it.title for it in items[:5] if it.title]
        summary = (
            f"{len(items)} headlines were curated for this category. "
            f"Overall sentiment is {sentiment.label.lower()} ({sentiment.score:.3f}). "
            + (f"Top story: {top_titles[0]}." if top_titles else "")
        ).strip()

        notable = []
        for it in items[: min(8, len(items))]:
            title = (it.title or "").strip()
            if not title:
                continue
            note = (it.summary or "").strip()
            note = note[:220] + ("…" if len(note) > 220 else "")
            if not note:
                note = "This item is noteworthy based on headline prominence in the feed."
            notable.append(
                {
                    "headline": title,
                    "why_it_matters": note,
                    "signal": "Opportunity" if sentiment.score > 0.1 else "Risk" if sentiment.score < -0.1 else "Unclear",
                }
            )

        return {
            "summary": summary,
            "key_themes": top_titles[:5] if len(top_titles) >= 3 else [
                "Top headlines",
                "Sentiment trend",
                "Developing stories",
            ],
            "notable_headlines": notable[: min(8, len(notable))],
            "future_outlook": {
                "next_24_72_hours": [
                    "Track updates to the leading stories listed above.",
                    "Watch for clarifications or official responses in follow-up coverage.",
                    "Expect sentiment to move as new details emerge.",
                ],
                "next_1_4_weeks": [
                    "Some stories may transition from breaking news to policy or market impact.",
                    "Recurring themes in the feed will indicate sustained momentum.",
                    "Cross-category spillover effects may become clearer with additional reporting.",
                ],
                "watch_list": top_titles[:4] if len(top_titles) >= 4 else [
                    "Top recurring headline",
                    "Regulatory/official updates",
                    "Industry reaction",
                    "Public sentiment shifts",
                ],
                "confidence": "Medium",
            },
            "caveats": [
                "This fallback report is generated from RSS headlines and summaries only.",
                "Verify key details by opening the source links in the headlines list.",
            ],
        }
