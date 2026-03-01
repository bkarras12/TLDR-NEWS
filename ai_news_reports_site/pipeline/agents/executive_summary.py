from __future__ import annotations

from typing import List

from openai import OpenAI

from .base import NewsItem, SentimentResult
from .openai_compat import chat_completion_text


class ExecutiveSummaryAgent:
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
    ) -> str:
        if not items:
            return "No headlines were available from the RSS feed at generation time."

        prompt = f"""Write a concise executive summary (2-4 sentences) for today's {category_title} report.

SOURCE: {source_name}
SENTIMENT:
- label: {sentiment.label}
- score: {sentiment.score:.3f}
- note: {sentiment.rationale}

HEADLINES:
{self._items_to_prompt(items)}

Use only the supplied headlines and summaries. Do not invent facts.
"""

        res = chat_completion_text(
            client=self.client,
            model=self.model,
            system="You are a neutral news editor. Write clear, factual summaries.",
            user=prompt,
            fallback_models=["gpt-4o-mini", "gpt-4o"],
            temperature=0.2,
        )
        return res.text
