# X Posting Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically post one tweet per news category daily to X, staggered 20 minutes apart, with an AI-generated hook line and sentiment score.

**Architecture:** TweetWriterAgent generates tweet text during the pipeline run and saves it into the report JSON. A separate lightweight script (`post_tweets.py`) reads the report and posts a single category's tweet via tweepy. A new GitHub Actions workflow calls that script on 5 staggered cron schedules.

**Tech Stack:** Python 3.11, tweepy (X API v2), OpenAI (via existing `openai_compat.py`), GitHub Actions cron

---

### Task 1: Add tweepy dependency

**Files:**
- Modify: `ai_news_reports_site/requirements.txt`

**Step 1: Add tweepy to requirements**

Add `tweepy>=4.14.0` to `requirements.txt`:

```
openai>=1.40.0
requests>=2.31.0
feedparser>=6.0.11
vaderSentiment>=3.3.2
python-dateutil>=2.9.0.post0
tweepy>=4.14.0
```

**Step 2: Commit**

```bash
git add ai_news_reports_site/requirements.txt
git commit -m "Add tweepy dependency for X posting"
```

---

### Task 2: Create TweetWriterAgent

**Files:**
- Create: `ai_news_reports_site/pipeline/agents/tweet_writer.py`

**Step 1: Create the agent**

```python
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
```

**Step 2: Commit**

```bash
git add ai_news_reports_site/pipeline/agents/tweet_writer.py
git commit -m "Add TweetWriterAgent for X posting"
```

---

### Task 3: Integrate TweetWriterAgent into run_daily.py

**Files:**
- Modify: `ai_news_reports_site/pipeline/run_daily.py`

**Step 1: Add import**

At the top of `run_daily.py`, after the existing agent imports (line 21), add:

```python
from pipeline.agents.tweet_writer import TweetWriterAgent
```

**Step 2: Generate tweet text per category**

After the categories loop builds `categories_out` (after line 273), add tweet generation. Insert before the trending topics section (before line 275):

```python
    # Generate tweet text for each category
    tweet_writer = TweetWriterAgent(client=client, model=model)
    for key, cat_data in categories_out.items():
        cat_items = [
            NewsItem(
                title=it["title"],
                url=it["url"],
                published=it.get("published"),
                summary=it.get("summary"),
                source=it.get("source"),
            )
            for it in cat_data.get("items", [])
        ]
        cat_sentiment = SentimentResult(
            score=cat_data["sentiment"]["score"],
            label=cat_data["sentiment"]["label"],
            rationale=cat_data["sentiment"]["rationale"],
        )
        tweet = tweet_writer.run(
            category_title=cat_data["title"],
            items=cat_items,
            sentiment=cat_sentiment,
        )
        if tweet:
            cat_data["tweet_text"] = tweet
            print(f"[{key}] Tweet: {tweet[:80]}...")
```

**Step 3: Commit**

```bash
git add ai_news_reports_site/pipeline/run_daily.py
git commit -m "Integrate TweetWriterAgent into daily pipeline"
```

---

### Task 4: Create post_tweets.py script

**Files:**
- Create: `ai_news_reports_site/pipeline/post_tweets.py`

This script is called by the posting workflow. It takes a category index (0-4) as an argument, reads today's report JSON, and posts the tweet for that category.

**Step 1: Create the script**

```python
"""Post a single category tweet to X.

Usage:
    python -m pipeline.post_tweets <category_index>

Environment variables:
    X_API_KEY          - X API key (OAuth 1.0a)
    X_API_SECRET       - X API key secret
    X_CONSUMER_KEY     - X consumer / access token
    X_CONSUMER_SECRET  - X consumer / access token secret
    X_DRY_RUN          - Set to "true" to print without posting
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


TZ = "America/Denver"


def _today_key() -> str:
    return datetime.now(ZoneInfo(TZ)).strftime("%Y-%m-%d")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.post_tweets <category_index>", file=sys.stderr)
        return 1

    cat_index = int(sys.argv[1])
    dry_run = os.getenv("X_DRY_RUN", "").strip().lower() == "true"

    date_key = _today_key()
    site_root = Path(__file__).resolve().parents[1]
    report_path = site_root / "news" / "data" / "reports" / f"{date_key}.json"

    if not report_path.exists():
        print(f"No report found for {date_key} at {report_path}", file=sys.stderr)
        return 1

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    categories = report.get("categories", {})
    cat_keys = list(categories.keys())

    if cat_index < 0 or cat_index >= len(cat_keys):
        print(f"Category index {cat_index} out of range (0-{len(cat_keys) - 1})", file=sys.stderr)
        return 1

    key = cat_keys[cat_index]
    cat_data = categories[key]
    tweet_text = cat_data.get("tweet_text", "")

    if not tweet_text:
        print(f"[{key}] No tweet_text found, skipping.", file=sys.stderr)
        return 0

    print(f"[{key}] Tweet ({len(tweet_text)} chars):\n{tweet_text}\n")

    if dry_run:
        print("[DRY RUN] Tweet not posted.")
        return 0

    # Post to X
    api_key = os.getenv("X_API_KEY", "").strip()
    api_secret = os.getenv("X_API_SECRET", "").strip()
    consumer_key = os.getenv("X_CONSUMER_KEY", "").strip()
    consumer_secret = os.getenv("X_CONSUMER_SECRET", "").strip()

    if not all([api_key, api_secret, consumer_key, consumer_secret]):
        print("ERROR: Missing X API credentials. Set X_API_KEY, X_API_SECRET, X_CONSUMER_KEY, X_CONSUMER_SECRET.", file=sys.stderr)
        return 1

    import tweepy

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=consumer_key,
        access_token_secret=consumer_secret,
    )

    try:
        response = client.create_tweet(text=tweet_text)
        tweet_id = response.data["id"]
        print(f"[{key}] Posted tweet: https://x.com/tldrnewsusa/status/{tweet_id}")
    except Exception as e:
        print(f"[{key}] ERROR posting tweet: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 2: Commit**

```bash
git add ai_news_reports_site/pipeline/post_tweets.py
git commit -m "Add post_tweets.py script for X API posting"
```

---

### Task 5: Create post_tweets.yml workflow

**Files:**
- Create: `.github/workflows/post_tweets.yml`

**Step 1: Create the workflow**

The 5 cron times are staggered 20 minutes apart, starting 20 minutes after the daily pipeline (14:10 UTC):
- 14:30 UTC — category 0 (world)
- 14:50 UTC — category 1 (business)
- 15:10 UTC — category 2 (technology)
- 15:30 UTC — category 3 (sports)
- 15:50 UTC — category 4 (science)

```yaml
name: Post to X

on:
  workflow_dispatch:
    inputs:
      category_index:
        description: "Category index to post (0-4)"
        required: true
        default: "0"
  schedule:
    - cron: "30 14 * * *"  # world
    - cron: "50 14 * * *"  # business
    - cron: "10 15 * * *"  # technology
    - cron: "30 15 * * *"  # sports
    - cron: "50 15 * * *"  # science

jobs:
  post-tweet:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        working-directory: ai_news_reports_site
        run: |
          python -m pip install --upgrade pip
          pip install tweepy>=4.14.0

      - name: Determine category index
        id: cat
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            echo "index=${{ github.event.inputs.category_index }}" >> "$GITHUB_OUTPUT"
          else
            # Map cron minute to category index
            MINUTE=$(date -u +%M)
            HOUR=$(date -u +%H)
            if [ "$HOUR" = "14" ] && [ "$MINUTE" -lt "45" ]; then
              echo "index=0" >> "$GITHUB_OUTPUT"
            elif [ "$HOUR" = "14" ]; then
              echo "index=1" >> "$GITHUB_OUTPUT"
            elif [ "$HOUR" = "15" ] && [ "$MINUTE" -lt "25" ]; then
              echo "index=2" >> "$GITHUB_OUTPUT"
            elif [ "$HOUR" = "15" ] && [ "$MINUTE" -lt "45" ]; then
              echo "index=3" >> "$GITHUB_OUTPUT"
            else
              echo "index=4" >> "$GITHUB_OUTPUT"
            fi
          fi

      - name: Post tweet
        working-directory: ai_news_reports_site
        env:
          X_API_KEY: ${{ secrets.X_API_KEY }}
          X_API_SECRET: ${{ secrets.X_API_SECRET }}
          X_CONSUMER_KEY: ${{ secrets.X_CONSUMER_KEY }}
          X_CONSUMER_SECRET: ${{ secrets.X_CONSUMER_SECRET }}
        run: |
          python -m pipeline.post_tweets ${{ steps.cat.outputs.index }}
```

**Step 2: Commit**

```bash
git add .github/workflows/post_tweets.yml
git commit -m "Add staggered X posting workflow"
```

---

### Task 6: Manual verification

**Step 1: Run pipeline locally to generate tweet_text fields**

```bash
cd ai_news_reports_site
export OPENAI_API_KEY="sk-..."
python -m pipeline.run_daily
```

Verify: Check today's report JSON for `tweet_text` fields in each category.

**Step 2: Test dry-run posting**

```bash
export X_DRY_RUN="true"
python -m pipeline.post_tweets 0
python -m pipeline.post_tweets 1
python -m pipeline.post_tweets 2
python -m pipeline.post_tweets 3
python -m pipeline.post_tweets 4
```

Verify: Each prints the tweet text and "[DRY RUN] Tweet not posted."

**Step 3: Add GitHub Secrets**

Go to repo Settings > Secrets and variables > Actions and add:
- `X_API_KEY`
- `X_API_SECRET`
- `X_CONSUMER_KEY`
- `X_CONSUMER_SECRET`

**Step 4: Push and test**

```bash
git push
```

Then trigger the daily pipeline via workflow_dispatch, followed by the post workflow with category_index=0 to verify end-to-end.
