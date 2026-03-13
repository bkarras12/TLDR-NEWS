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

MAX_CHARS = 280


def _is_promotional(text: str) -> bool:
    """Check if reply text contains promotional language."""
    lower = text.lower()
    return any(p in lower for p in _PROMO_PATTERNS)


def _has_profanity(text: str) -> bool:
    """Check if text contains profanity."""
    words = set(re.sub(r"[^a-zA-Z\s]", "", text.lower()).split())
    return bool(words & _PROFANITY)


def _truncate_to_limit(text: str, limit: int = MAX_CHARS) -> str:
    """Truncate text at last sentence boundary under limit, or last word boundary."""
    if len(text) <= limit:
        return text

    # Try to cut at last sentence-ending punctuation under limit
    truncated = text[:limit]
    for punct in [". ", "! ", "? "]:
        idx = truncated.rfind(punct)
        if idx > 60:  # Must keep at least 60 chars
            return truncated[: idx + 1].strip()

    # Fall back to last space
    idx = truncated.rfind(" ")
    if idx > 60:
        return truncated[:idx].strip()

    # Last resort: hard cut
    return truncated.strip()


class ReplyWriterAgent:
    """Generates conversational, passionate quote-tweet commentary."""

    def __init__(self, client: Any | None, model: str):
        self.client = client
        self.model = model

    def _generate(self, system: str, user: str) -> Optional[str]:
        """Call OpenAI and return stripped text, or None on failure."""
        try:
            result = chat_completion_text(
                client=self.client,
                model=self.model,
                system=system,
                user=user,
                fallback_models=["gpt-4o-mini", "gpt-4o"],
                temperature=0.8,
            )
            return result.text.strip().strip('"').strip("'")
        except Exception as e:
            print(f"[reply_writer] ERROR: {type(e).__name__}: {e}", flush=True)
            return None

    def run(
        self,
        *,
        tweet_text: str,
        category_context: Dict[str, Any],
    ) -> Optional[str]:
        """Generate quote-tweet commentary. Returns text or None."""
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
            "You write short, punchy quote tweets — ONE or TWO sentences MAX.\n\n"

            "You are a passionate news commentator adding your take to a trending tweet. "
            "You sound like a real person, not a brand or bot.\n\n"

            "CRITICAL LENGTH RULE:\n"
            "- Your response MUST be 1-2 sentences.\n"
            "- Keep it under 200 characters. Shorter is ALWAYS better.\n"
            "- If you can say it in 15 words, don't use 30.\n\n"

            "Style:\n"
            "- Conversational, passionate, opinionated\n"
            "- Add one specific fact, connection, or fresh angle\n"
            "- Your text stands alone (the quoted tweet appears below it)\n\n"

            "Banned:\n"
            "- NO hashtags, emojis, links, or URLs\n"
            "- NO promotional language\n"
            "- NO 'Great point', 'So true', or similar openers\n"
            "- Do NOT repeat or paraphrase the original tweet\n"
            "- Output ONLY the commentary text, nothing else"
        )

        user = (
            f"Write a quote tweet (under 200 characters, 1-2 sentences) for:\n"
            f'"{tweet_text}"\n\n'
            f"Your {cat_title} news context:\n"
            f"Sentiment: {sent_label}\n"
            f"Themes: {', '.join(themes)}\n"
            f"Summary: {summary}\n"
            f"Notable:\n{notable_text}"
        )

        # Attempt 1
        reply = self._generate(system, user)
        if reply is None:
            return None

        # If too long, retry once with explicit shortening instruction
        if len(reply) > MAX_CHARS:
            print(f"[reply_writer] Too long ({len(reply)} chars), retrying shorter...")
            shorten_user = (
                f"Your previous quote tweet was {len(reply)} characters — way too long. "
                f"Rewrite it in ONE short sentence under 150 characters. Be blunt and direct.\n\n"
                f"Original tweet: \"{tweet_text}\"\n"
                f"Your previous attempt: \"{reply}\"\n\n"
                f"Write a shorter version. ONE sentence. Under 150 characters. Output ONLY the text."
            )
            reply = self._generate(system, shorten_user)
            if reply is None:
                return None

        # If STILL too long after retry, truncate at sentence boundary
        if len(reply) > MAX_CHARS:
            print(f"[reply_writer] Still too long ({len(reply)} chars), truncating...")
            reply = _truncate_to_limit(reply, MAX_CHARS)

        return self._validate(reply)

    @staticmethod
    def _validate(reply: str) -> Optional[str]:
        """Validate reply passes quality checks. Returns reply or None."""
        if not reply or len(reply) < 30:
            print(f"[reply_writer] Rejected: too short ({len(reply)} chars)")
            return None
        if len(reply) > MAX_CHARS:
            print(f"[reply_writer] Rejected: too long ({len(reply)} chars)")
            return None
        if _is_promotional(reply):
            print(f"[reply_writer] Rejected: promotional language detected")
            return None
        if _has_profanity(reply):
            print(f"[reply_writer] Rejected: profanity detected")
            return None
        return reply
