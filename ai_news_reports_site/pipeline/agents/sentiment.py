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
        if not items:
            return SentimentResult(score=0.0, label="Neutral", rationale="No headlines were available to score.")

        # Score each headline individually, then average — prevents a single
        # strongly-worded block of text from dominating the category score.
        scores = []
        for it in items:
            parts = [it.title]
            if it.summary:
                parts.append(it.summary)
            text = " ".join(parts).strip()
            if text:
                scores.append(float(self._analyzer.polarity_scores(text)["compound"]))

        if not scores:
            return SentimentResult(score=0.0, label="Neutral", rationale="No headlines were available to score.")

        # Dampen: average the per-item scores then apply a 0.6 weight toward
        # neutral so results cluster in the -0.4 .. +0.4 range instead of
        # swinging to the extremes.
        raw_avg = sum(scores) / len(scores)
        score = round(raw_avg * 0.6, 4)

        label = self._label(score)

        rationale = (
            f"Average of {len(scores)} per-headline sentiment scores (raw avg {raw_avg:+.3f}, "
            f"dampened ×0.6 → {score:+.4f}). "
            "This is a coarse signal; interpret as overall tone, not factual positivity/negativity."
        )

        return SentimentResult(score=score, label=label, rationale=rationale)
