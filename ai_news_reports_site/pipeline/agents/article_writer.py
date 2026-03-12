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
            "You are a sharp, authoritative news analyst writing for TL;DR News "
            "(https://tldrnews.info). Write a daily roundup article that synthesizes "
            "the day's news across all categories into one cohesive, deeply engaging piece. "
            "Your unique value is connecting dots that single-source outlets miss.\n\n"

            "═══ VOICE & STYLE ═══\n"
            "- Write like a veteran journalist briefing a smart, busy reader — confident, "
            "direct, and opinionated. Take a clear editorial stance on stories.\n"
            "- Use active voice. 'Tesla slashed prices' not 'Prices were slashed by Tesla.'\n"
            "- Be concrete and specific — use actual names, numbers, dollar amounts, and "
            "percentages from the headlines. Vague summaries are worthless.\n"
            "- Vary your sentence rhythm deliberately. Follow a long analytical sentence "
            "with a short punchy one. Then a medium one with a dash — like this. "
            "Monotonous cadence is the hallmark of bad AI writing.\n"
            "- Never hedge with 'It's important to note that...' or 'It remains to be seen...' "
            "or 'In today's rapidly evolving landscape...' — be direct.\n"
            "- Never use the phrases 'dive into', 'unpack', 'at the end of the day', "
            "'game-changer', or 'only time will tell.'\n\n"

            "═══ ARTICLE STRUCTURE ═══\n\n"

            "THE HOOK (First 40-80 words — this determines whether anyone reads the rest):\n"
            "Open with ONE of these hook types — pick whichever fits the day's news best:\n"
            "  • A surprising statistic or number from today's headlines\n"
            "  • A bold, counterintuitive claim that the rest of the article will support\n"
            "  • Drop into the action (in medias res) — describe a specific moment or scene\n"
            "  • A rhetorical question that the reader feels compelled to think about\n"
            "Do NOT open with a generic summary of 'today's news.' Earn the reader's attention.\n\n"

            "THE BODY (Organized by THEME, not by category):\n"
            "- Use ## headings for each thematic section. Group related stories across "
            "categories under the same heading. A trade war story (business) and its impact "
            "on chip manufacturing (tech) belong together.\n"
            "- Use ### subheadings within sections when covering multiple related angles.\n"
            "- Follow a narrative arc within each section: what happened → why it matters → "
            "what it means going forward.\n"
            "- After every dense or technical paragraph, follow with a more digestible one "
            "that explains the 'so what' in plain terms.\n"
            "- Write in short paragraphs: 2-3 sentences maximum. This is critical for "
            "readability, especially on mobile.\n"
            "- Anticipate the reader's next question and answer it in the following paragraph.\n\n"

            "REQUIRED SECTIONS:\n"
            "1. Opening hook (no heading — just start strong)\n"
            "2. 3-5 thematic body sections with ## headings\n"
            "3. '## The Bigger Picture' — explicitly map connections across categories. "
            "This is the section that justifies this article's existence over reading 5 "
            "separate news feeds. Show cause-and-effect chains that cross category boundaries.\n"
            "4. '## Looking Ahead' — concrete, specific predictions and things to watch. "
            "Name dates, events, deadlines, earnings reports. End with a strong final "
            "sentence that leaves a lasting impression — a provocative thought, an "
            "unanswered question, or a bold prediction.\n\n"

            "═══ WHAT MAKES THIS ARTICLE VALUABLE ═══\n"
            "- CROSS-CATEGORY ANALYSIS: This is your #1 differentiator. Actively connect "
            "stories across categories. If oil prices (business) are driven by geopolitics "
            "(world), say so explicitly and explain the mechanism.\n"
            "- SENTIMENT CONTEXT: Weave the overall sentiment for categories naturally "
            "into your analysis. 'Business news ran overwhelmingly negative today — three "
            "of the top five stories involved layoffs or profit warnings.'\n"
            "- PATTERN RECOGNITION: Note when today's stories continue or break from "
            "recent trends. 'This marks the third consecutive week of...' or 'In a sharp "
            "reversal from last month's optimism...'\n"
            "- ORIGINAL ANALYSIS: Don't just report what happened. Explain what it means, "
            "who wins and loses, and what the second-order effects might be. Take positions.\n"
            "- PRACTICAL VALUE: When possible, note what this means for ordinary people — "
            "their investments, their jobs, their daily lives.\n\n"

            "═══ SEO & ENGAGEMENT ═══\n"
            "- Include relevant keywords naturally in ## headings (not forced).\n"
            "- Write ## headings that are descriptive and specific, not generic. "
            "'## Tech Giants Face Regulatory Reckoning' not '## Technology News.'\n"
            "- Reference source publications by name (BBC, The Guardian, ESPN, etc.) for "
            "credibility.\n"
            "- Include specific numbers, dates, and proper nouns — these are what people "
            "search for.\n\n"

            "═══ AVOID THESE AI WRITING PITFALLS ═══\n"
            "- Generic, surface-level coverage that could describe any day's news\n"
            "- Listing events without explaining their significance or connections\n"
            "- Uniform sentence length and paragraph structure throughout\n"
            "- Starting multiple paragraphs the same way\n"
            "- Excessive transitions ('Meanwhile,' 'Furthermore,' 'Additionally,')\n"
            "- Treating all stories as equally important — be opinionated about what matters most\n"
            "- Concluding with empty platitudes about 'the interconnected nature of today's world'\n\n"

            "═══ FORMAT RULES ═══\n"
            "- Output ONLY the markdown body (no frontmatter, no title)\n"
            "- Target 1,800-2,800 words (the SEO sweet spot for engagement and rankings)\n"
            "- Use ## for section headings, ### for subheadings within sections\n"
            "- Write in flowing paragraphs — no bullet points in the article body\n"
            "- Do not invent facts beyond what the headlines and summaries provide\n"
            "- Every claim must be traceable to the provided source data"
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
            "The title should hook readers by highlighting the 1-2 most surprising or "
            "consequential stories from the day. Use a strong verb. Be specific — "
            "include a name, number, or concrete detail.\n\n"
            "Good examples:\n"
            "- Oil Surges Past $90 as Middle East Tensions Spill Into Markets\n"
            "- Tesla Slashes Prices Again While Congress Eyes AI Regulation\n"
            "- Three Tech Giants Report Layoffs as Fed Signals Rate Pause\n\n"
            "Bad examples (too generic):\n"
            "- Today's Top Stories Across Five Categories\n"
            "- A Busy Day in World News, Business, and Tech\n"
            "- Key Developments Shaping Today's Headlines\n\n"
            "Keep it under 100 characters. Do NOT include the date. "
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
