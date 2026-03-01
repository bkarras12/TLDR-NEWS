from __future__ import annotations

from typing import List

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .base import NewsItem, SentimentResult


class SentimentAgent:
    def __init__(self):
        self._analyzer = SentimentIntensityAnalyzer()

    @staticmethod
    def _label(score: float) -> str:
        # Conservative buckets (news often "mixed")
        if score >= 0.25:
            return "Positive"
        if score <= -0.25:
            return "Negative"
        if -0.05 <= score <= 0.05:
            return "Neutral"
        return "Mixed"

    def run(self, items: List[NewsItem]) -> SentimentResult:
        text_parts = []
        for it in items:
            text_parts.append(it.title)
            if it.summary:
                text_parts.append(it.summary)

        text = "\n".join(text_parts).strip()
        if not text:
            return SentimentResult(score=0.0, label="Neutral", rationale="No headlines were available to score.")

        score = float(self._analyzer.polarity_scores(text)["compound"])
        label = self._label(score)

        rationale = (
            "Computed using a lexicon-based sentiment model over the combined headlines + summaries. "
            "This is a coarse signal; interpret as overall tone, not factual positivity/negativity."
        )

        return SentimentResult(score=score, label=label, rationale=rationale)
