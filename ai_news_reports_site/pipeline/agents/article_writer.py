from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .openai_compat import chat_completion_text


class ArticleWriterAgent:
    """Generates a daily roundup article in Markdown from the day's report data."""

    def __init__(self, client: Any | None, model: str):
        self.client = client
        self.model = model

    def run(
        self,
        *,
        date_key: str,
        daily_report: Dict[str, Any],
    ) -> Optional[str]:
        """Generate a markdown article from the daily report. Returns markdown string or None."""
        if self.client is None:
            return None

        categories = daily_report.get("categories", {})
        if not categories:
            return None

        prompt_sections = []
        for cat_key, cat_data in categories.items():
            title = cat_data.get("title", cat_key)
            ai = cat_data.get("ai_report", {})
            sent = cat_data.get("sentiment", {})
            summary = ai.get("summary", "")
            themes = ai.get("key_themes", [])
            headlines = []
            for item in cat_data.get("items", [])[:8]:
                h = item.get("title", "")
                s = item.get("summary", "")
                if h:
                    headlines.append(f"  - {h}" + (f": {s}" if s else ""))

            notable = []
            for nh in ai.get("notable_headlines", [])[:5]:
                notable.append(f"  - {nh.get('headline', '')}: {nh.get('why_it_matters', '')}")

            sentiment_line = f"Sentiment: {sent.get('label', 'N/A')} ({sent.get('score', 'N/A')})"

            prompt_sections.append(
                f"## {title}\n"
                f"{sentiment_line}\n"
                f"Summary: {summary}\n"
                f"Key themes: {', '.join(themes)}\n"
                f"Headlines:\n" + "\n".join(headlines) + "\n"
                f"Notable:\n" + "\n".join(notable)
            )

        report_blob = "\n\n".join(prompt_sections)

        system = (
            "You are a sharp, engaging news analyst for TL;DR News. Write a daily roundup article "
            "that synthesizes the day's news across all categories into one cohesive, readable piece. "
            "Your unique value is connecting dots that single-source outlets miss.\n\n"
            "Your writing style is:\n"
            "- Conversational but authoritative, like a well-informed friend briefing you\n"
            "- Concrete and specific — use actual names, numbers, and details from the headlines\n"
            "- Analytical — don't just list what happened, explain why it matters and how stories connect\n"
            "- Cross-category — actively look for how a business story impacts tech, how world events affect sports, etc.\n"
            "- Efficient — every sentence earns its place\n\n"
            "IMPORTANT — What makes this article unique (not available from any single news source):\n"
            "- CROSS-CATEGORY ANALYSIS: Explicitly connect stories across different categories. "
            "If oil prices (business) are driven by geopolitics (world), say so. If a tech regulation affects business, connect them.\n"
            "- SENTIMENT CONTEXT: Reference the overall sentiment for each category naturally. "
            "E.g., 'The business category skewed heavily negative today, driven by...' or 'In a rare positive day for world news...'\n"
            "- PATTERN RECOGNITION: Note when today's stories continue or break from recent trends.\n\n"
            "Format rules:\n"
            "- Output ONLY the markdown body (no frontmatter, no title — those are added separately)\n"
            "- Use ## for section headings — organize by THEME, not by category. Group related stories together.\n"
            "- Write 1000-1800 words\n"
            "- Open with a punchy 2-3 sentence lede that captures the day's biggest themes\n"
            "- Include a '## The Bigger Picture' section that explicitly maps connections across categories\n"
            "- End with a short '## Looking Ahead' section\n"
            "- Do not invent facts beyond what the headlines and summaries provide\n"
            "- Do not use bullet points — write in flowing paragraphs"
        )

        trending = daily_report.get("trending_topics", [])
        trending_line = ""
        if trending:
            trending_line = f"\nTRENDING TOPICS (appearing across multiple categories): {', '.join(trending[:8])}\n"

        user = (
            f"Write today's daily roundup article for {date_key}.\n"
            f"{trending_line}\n"
            f"Here is the full report data across all categories:\n\n{report_blob}"
        )

        try:
            result = chat_completion_text(
                client=self.client,
                model=self.model,
                system=system,
                user=user,
                fallback_models=["gpt-4o-mini", "gpt-4o"],
                temperature=0.7,
            )
            body = result.text.strip()
            if not body or len(body) < 200:
                return None
            return body
        except Exception as e:
            print(f"[article] ERROR generating article: {type(e).__name__}: {e}")
            return None

    @staticmethod
    def build_frontmatter(
        *,
        date_key: str,
        title: str,
        category: str = "world",
    ) -> str:
        return (
            f"---\n"
            f'title: "{title}"\n'
            f"category: {category}\n"
            f"date: {date_key}\n"
            f"author: TL;DR News\n"
            f"---\n"
        )

    def generate_title(self, *, date_key: str, daily_report: Dict[str, Any]) -> str:
        """Generate a compelling article title from the report data."""
        if self.client is None:
            return f"Daily News Roundup — {date_key}"

        categories = daily_report.get("categories", {})
        takeaways = []
        for cat_data in categories.values():
            ai = cat_data.get("ai_report", {})
            kt = ai.get("key_takeaway", "")
            if kt:
                takeaways.append(f"- {cat_data.get('title', '')}: {kt}")

        system = (
            "You generate punchy, specific article titles for a daily news roundup. "
            "The title should highlight 2-3 of the biggest stories from the day, "
            "separated by commas or 'and'. Keep it under 100 characters. "
            "Do NOT use generic titles like 'Today's News Roundup'. "
            "Do NOT include the date. "
            "Output ONLY the title text, nothing else."
        )

        user = f"Key takeaways for {date_key}:\n" + "\n".join(takeaways)

        try:
            result = chat_completion_text(
                client=self.client,
                model=self.model,
                system=system,
                user=user,
                fallback_models=["gpt-4o-mini", "gpt-4o"],
                temperature=0.8,
            )
            title = result.text.strip().strip('"').strip("'")
            if title and len(title) > 10:
                return title
        except Exception:
            pass

        return f"Daily News Roundup — {date_key}"

    def write_article(
        self,
        *,
        site_root: Path,
        date_key: str,
        daily_report: Dict[str, Any],
    ) -> Optional[Path]:
        """Generate and write article + update index. Returns path or None."""
        body = self.run(date_key=date_key, daily_report=daily_report)
        if body is None:
            return None

        title = self.generate_title(date_key=date_key, daily_report=daily_report)
        frontmatter = self.build_frontmatter(date_key=date_key, title=title)
        markdown = frontmatter + "\n" + body + "\n"

        articles_dir = site_root / "news" / "articles"
        articles_dir.mkdir(parents=True, exist_ok=True)

        slug = f"{date_key}-daily-roundup"
        article_path = articles_dir / f"{slug}.md"
        article_path.write_text(markdown, encoding="utf-8")

        # Update articles index
        index_path = articles_dir / "articles_index.json"
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            index = []

        # Remove existing entry for same slug
        index = [e for e in index if e.get("slug") != slug]

        index.insert(0, {
            "slug": slug,
            "title": title,
            "category": "world",
            "date": date_key,
            "author": "TL;DR News",
        })

        # Keep last 90 articles
        index = index[:90]

        index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

        return article_path
