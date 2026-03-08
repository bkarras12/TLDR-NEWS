from __future__ import annotations

from typing import Any, List, Optional

from .base import NewsItem, SentimentResult
from .openai_compat import chat_completion_text


class TweetWriterAgent:
    """Generates a short, emotion-sparking tweet for a news category."""

    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    @staticmethod
    def _fallback_tweet(
        category_title: str,
        items: List[NewsItem],
        sentiment: SentimentResult,
    ) -> str:
        """Deterministic fallback when OpenAI is unavailable."""
        top = items[0].title if items else "Top stories"
        sign = "+" if sentiment.score >= 0 else ""
        return (
            f"{category_title}: {top}\n\n"
            f"Sentiment: {sentiment.label} ({sign}{sentiment.score:.2f})\n\n"
            f"Read the full breakdown: https://tldrnews.info"
        )

    def run(
        self,
        *,
        category_title: str,
        items: List[NewsItem],
        sentiment: SentimentResult,
    ) -> str:
        """Return tweet text (≤280 chars) for one category."""

        if not items:
            return ""

        if self.client is None:
            return self._fallback_tweet(category_title, items, sentiment)

        headlines = "\n".join(f"- {it.title}" for it in items[:6])
        sign = "+" if sentiment.score >= 0 else ""
        sentiment_line = f"Sentiment: {sentiment.label} ({sign}{sentiment.score:.2f})"

        prompt = f"""Write a single tweet (max 200 characters) about today's {category_title} news.

HEADLINES:
{headlines}

Requirements:
- Emotion-sparking hook that makes people want to click
- Do NOT use hashtags
- Do NOT use emojis
- Write only the hook line, nothing else

I will append the sentiment score and link myself, so only write the hook."""

        try:
            result = chat_completion_text(
                client=self.client,
                model=self.model,
                system="You are a social media copywriter. Write punchy, attention-grabbing one-liners for news.",
                user=prompt,
                fallback_models=["gpt-4o-mini", "gpt-4o"],
                temperature=0.7,
            )
            hook = result.text.strip().strip('"').strip("'")
            # Truncate hook if needed to fit full tweet under 280 chars
            max_hook = 280 - len(f"\n\n{sentiment_line}\n\nRead the full breakdown: https://tldrnews.info")
            if len(hook) > max_hook:
                hook = hook[: max_hook - 3].rsplit(" ", 1)[0] + "..."

            return f"{hook}\n\n{sentiment_line}\n\nRead the full breakdown: https://tldrnews.info"
        except Exception as e:
            print(f"[tweet_writer] OpenAI failed: {e}", flush=True)
            return self._fallback_tweet(category_title, items, sentiment)
