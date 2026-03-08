from __future__ import annotations

import re
from typing import Any, List

from .base import NewsItem, SentimentResult
from .openai_compat import chat_completion_text


# Always appended to every tweet
BASE_HASHTAGS = ["#BreakingNews", "#News", "#WorldNews", "#Headlines", "#Trending"]

# Category-specific hashtag overrides
CATEGORY_HASHTAGS = {
    "world": "#WorldNews",
    "business": "#Business",
    "technology": "#Tech",
    "sports": "#Sports",
    "science": "#Science",
}

# Common words that make poor hashtags
_HASHTAG_STOP = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "has",
    "her", "was", "one", "our", "out", "his", "how", "its", "may", "new",
    "now", "say", "she", "too", "use", "will", "with", "from", "have",
    "been", "that", "this", "what", "when", "who", "more", "some", "than",
    "them", "then", "into", "over", "also", "back", "after", "year", "years",
    "just", "most", "about", "being", "could", "first", "would", "other",
    "their", "there", "these", "those", "which", "people", "says", "said",
    "report", "reports", "according", "news",
}


def _extract_buzz_hashtags(items: List[NewsItem], max_tags: int = 3) -> List[str]:
    """Extract buzz-worthy words from headlines and turn them into hashtags."""
    word_count: dict[str, int] = {}
    for item in items[:8]:
        words = re.sub(r"[^a-zA-Z0-9\s]", "", item.title).split()
        for w in words:
            lower = w.lower()
            if len(lower) >= 4 and lower not in _HASHTAG_STOP:
                word_count[lower] = word_count.get(lower, 0) + 1

    # Sort by frequency, then alphabetically for stability
    ranked = sorted(word_count.items(), key=lambda x: (-x[1], x[0]))
    tags = []
    for word, _ in ranked:
        tag = f"#{word.capitalize()}"
        if tag not in tags:
            tags.append(tag)
        if len(tags) >= max_tags:
            break
    return tags


def _build_hashtag_line(category_key: str, items: List[NewsItem]) -> str:
    """Build the hashtag line for a tweet."""
    buzz = _extract_buzz_hashtags(items)
    cat_tag = CATEGORY_HASHTAGS.get(category_key)

    # Combine: buzz words + category tag + base tags, deduplicated
    all_tags: List[str] = []
    for tag in buzz:
        if tag not in all_tags:
            all_tags.append(tag)
    if cat_tag and cat_tag not in all_tags:
        all_tags.append(cat_tag)
    for tag in BASE_HASHTAGS:
        if tag not in all_tags:
            all_tags.append(tag)

    return " ".join(all_tags)


class TweetWriterAgent:
    """Generates a short, emotion-sparking tweet for a news category."""

    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    @staticmethod
    def _build_tweet(hook: str, sentiment_line: str, hashtags: str) -> str:
        """Assemble tweet parts, truncating hook if needed to fit 280 chars."""
        suffix = f"\n\n{sentiment_line}\n\nRead the full breakdown: https://tldrnews.info\n\n{hashtags}"
        max_hook = 280 - len(suffix)
        if len(hook) > max_hook:
            hook = hook[: max_hook - 3].rsplit(" ", 1)[0] + "..."
        return hook + suffix

    def run(
        self,
        *,
        category_key: str = "",
        category_title: str,
        items: List[NewsItem],
        sentiment: SentimentResult,
    ) -> str:
        """Return tweet text (≤280 chars) for one category."""

        if not items:
            return ""

        sign = "+" if sentiment.score >= 0 else ""
        sentiment_line = f"{category_title} Sentiment: {sentiment.label} ({sign}{sentiment.score:.2f})"
        hashtags = _build_hashtag_line(category_key, items)

        if self.client is None:
            top = items[0].title if items else "Top stories"
            hook = f"{category_title}: {top}"
            return self._build_tweet(hook, sentiment_line, hashtags)

        headlines = "\n".join(f"- {it.title}" for it in items[:6])

        prompt = f"""Write a single tweet (max 140 characters) about today's {category_title} news.

HEADLINES:
{headlines}

Requirements:
- Emotion-sparking hook that makes people want to click
- Do NOT use hashtags (I will add them)
- Do NOT use emojis
- Write only the hook line, nothing else

I will append the sentiment score, hashtags, and link myself, so only write the hook."""

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
            return self._build_tweet(hook, sentiment_line, hashtags)
        except Exception as e:
            print(f"[tweet_writer] OpenAI failed: {e}", flush=True)
            top = items[0].title if items else "Top stories"
            hook = f"{category_title}: {top}"
            return self._build_tweet(hook, sentiment_line, hashtags)
