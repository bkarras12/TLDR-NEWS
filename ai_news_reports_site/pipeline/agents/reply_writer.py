from __future__ import annotations

import re
from typing import Any, Dict, Optional

from .openai_compat import chat_completion_text


# Promotional phrases that disqualify a reply
_PROMO_PATTERNS = [
    "check out", "read more", "click here", "visit our", "subscribe",
    "follow us", "check our", "see our", "link in", "tldrnews",
]

# Basic profanity list for outbound filtering
_PROFANITY = {
    "fuck", "shit", "bitch", "ass", "damn", "crap", "dick", "piss",
    "bastard", "slut", "whore", "nigger", "faggot", "retard",
}


def _is_promotional(text: str) -> bool:
    """Check if reply text contains promotional language."""
    lower = text.lower()
    return any(p in lower for p in _PROMO_PATTERNS)


def _has_profanity(text: str) -> bool:
    """Check if text contains profanity."""
    words = set(re.sub(r"[^a-zA-Z\s]", "", text.lower()).split())
    return bool(words & _PROFANITY)


class ReplyWriterAgent:
    """Generates conversational, passionate replies to tweets about trending news."""

    def __init__(self, client: Any | None, model: str):
        self.client = client
        self.model = model

    def run(
        self,
        *,
        tweet_text: str,
        category_context: Dict[str, Any],
    ) -> Optional[str]:
        """Generate a reply to a tweet. Returns reply text or None."""
        if self.client is None:
            return None

        cat_title = category_context.get("title", "News")
        summary = category_context.get("ai_report", {}).get("summary", "")
        themes = category_context.get("ai_report", {}).get("key_themes", [])
        sentiment = category_context.get("sentiment", {})
        sent_label = sentiment.get("label", "")

        notable = []
        for nh in category_context.get("ai_report", {}).get("notable_headlines", [])[:3]:
            notable.append(f"- {nh.get('headline', '')}: {nh.get('why_it_matters', '')}")
        notable_text = "\n".join(notable) if notable else "None available"

        system = (
            "You are a passionate, well-informed news enthusiast replying to someone's tweet. "
            "You genuinely care about what's happening in the world and have strong but "
            "respectful opinions. You sound like a real person — not a brand, not a bot, "
            "not a journalist.\n\n"

            "Your reply style:\n"
            "- Conversational and natural — like texting a friend who follows the news\n"
            "- Passionate — you have feelings about this stuff. Show it.\n"
            "- Opinionated — take a stance, agree or push back on the tweet's take\n"
            "- Add value — share a related fact, a connection they might not have made, "
            "or a perspective they haven't considered\n"
            "- Brief — this is a reply, not an essay. Get in, make your point, get out.\n\n"

            "Hard rules:\n"
            "- UNDER 280 characters. Shorter is better. Aim for 120-200 chars.\n"
            "- NO hashtags\n"
            "- NO emojis\n"
            "- NO links or URLs\n"
            "- NO promotional language (don't mention a website, brand, or say 'check out')\n"
            "- NO starting with 'Great point' or 'So true' or other sycophantic openers\n"
            "- Do NOT repeat the tweet back to them\n"
            "- Output ONLY the reply text, nothing else"
        )

        user = (
            f"Reply to this tweet:\n"
            f'"{tweet_text}"\n\n'
            f"Context you know from today's {cat_title} news:\n"
            f"Overall sentiment: {sent_label}\n"
            f"Key themes: {', '.join(themes)}\n"
            f"Summary: {summary}\n"
            f"Notable stories:\n{notable_text}\n\n"
            f"Write a passionate, conversational reply that adds value to this conversation."
        )

        try:
            result = chat_completion_text(
                client=self.client,
                model=self.model,
                system=system,
                user=user,
                fallback_models=["gpt-4o-mini", "gpt-4o"],
                temperature=0.8,
            )
            reply = result.text.strip().strip('"').strip("'")
            return self._validate(reply)
        except Exception as e:
            print(f"[reply_writer] ERROR: {type(e).__name__}: {e}", flush=True)
            return None

    @staticmethod
    def _validate(reply: str) -> Optional[str]:
        """Validate reply passes quality checks. Returns reply or None."""
        if not reply or len(reply) < 30:
            print(f"[reply_writer] Rejected: too short ({len(reply)} chars)")
            return None
        if len(reply) > 280:
            print(f"[reply_writer] Rejected: too long ({len(reply)} chars)")
            return None
        if _is_promotional(reply):
            print(f"[reply_writer] Rejected: promotional language detected")
            return None
        if _has_profanity(reply):
            print(f"[reply_writer] Rejected: profanity detected")
            return None
        return reply
