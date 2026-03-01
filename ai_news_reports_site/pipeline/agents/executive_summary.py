from __future__ import annotations

from typing import List

from openai import OpenAI

from .base import NewsItem, SentimentResult


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

        resp = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "developer",
                    "content": "You are a neutral news editor. Write clear, factual summaries.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return (resp.output_text or "").strip()
