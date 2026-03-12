# X Reply Agent — Design Spec

**Date:** 2026-03-12
**Status:** Approved

## Overview

A new reply agent that searches X for trending conversations related to today's news report, generates conversational and passionate AI-powered replies, and posts them. Targets 5-10 high-engagement tweets per day across two daily runs.

## Tweet Discovery

### Search Strategy

Two search strategies run in sequence:

1. **Trending topics** — Use the `trending_topics` list already detected by the daily pipeline (cross-category keywords). Search X for recent tweets discussing those topics.
2. **Notable headline keywords** — Extract specific names, companies, and events from `notable_headlines` across all categories. Search X for tweets about those.

### Filtering

Tweets must pass all filters to be considered:

- **Engagement minimum:** 5+ likes OR 3+ retweets (configurable via constants)
- **Recency:** Tweet must be less than 6 hours old
- **Not a reply:** Skip tweets that are already replies (depth > 0) — only reply to top-level tweets
- **Not self:** Skip tweets from @tldrnewsusa
- **Content filter:** Skip tweets containing profanity or slurs (basic word list)
- **Deduplication:** Skip tweets already replied to (checked against `replied_tweets.json`)

### Selection & Scoring

- Score each candidate: `score = likes + (retweets * 2)`
- Sort by score descending
- Take top 10 candidates maximum per run

## Reply Generation

### Agent: `ReplyWriterAgent`

- Takes: the source tweet text, the relevant category data from today's report (summary, key themes, notable headlines)
- Uses OpenAI (`chat_completion_text`) to generate a reply
- System prompt defines tone: conversational, passionate, opinionated — like someone who genuinely cares about this news and has a take on it

### Reply Rules

- Under 280 characters
- No hashtags (looks spammy in replies)
- No link to the site unless the reply specifically references a related story
- No emojis
- Must feel like a real person's reply, not a bot or an ad
- AI output is validated: reject if under 30 chars, if it contains "check out our", "read more at", or similar promotional language

### Fallback

- If AI generation fails for a tweet, skip it (do not fall back to templates — bad replies are worse than no replies)

## Architecture

### New Files

| File | Purpose |
|---|---|
| `pipeline/agents/reply_writer.py` | `ReplyWriterAgent` class — generates AI reply text given a tweet + report context |
| `pipeline/post_replies.py` | Standalone script — searches X, filters/scores tweets, generates replies, posts them |
| `news/data/replied_tweets.json` | Rolling log of tweet IDs already replied to (7-day retention window) |

### `ReplyWriterAgent` Interface

```python
class ReplyWriterAgent:
    def __init__(self, client, model): ...

    def run(self, *, tweet_text: str, category_context: dict) -> Optional[str]:
        """Generate a reply. Returns reply text or None if generation fails/is rejected."""
```

### `post_replies.py` Flow

```
1. Load today's report JSON
2. Extract search terms:
   a. trending_topics (top 8)
   b. Notable headline keywords (names, companies from notable_headlines)
3. For each search term, query X API (search_recent_tweets)
4. Merge results, deduplicate, apply filters
5. Score and rank by engagement
6. Take top N candidates (max 10)
7. For each candidate:
   a. Match to most relevant category from report
   b. Generate reply via ReplyWriterAgent
   c. Validate reply (length, no promo language)
   d. Post reply via tweepy (client.create_tweet with in_reply_to_tweet_id)
   e. Record tweet ID in replied_tweets.json
   f. Sleep 60 seconds before next reply
8. Clean up replied_tweets.json (remove entries older than 7 days)
```

### Usage

```bash
python -m pipeline.post_replies

# Dry run (no posting)
X_DRY_RUN=true python -m pipeline.post_replies
```

## Workflow Integration

### New workflow: `.github/workflows/post_replies.yml`

- **Triggers:** Schedule + manual dispatch
- **Schedule:** 2x daily
  - 15:30 UTC (8:30 AM MST) — after morning tweet batch
  - 00:30 UTC (5:30 PM MST) — after afternoon tweet batch
- **Secrets:** Same X API credentials as `post_tweets.yml` plus `OPENAI_API_KEY`
- **Steps:**
  1. Checkout repo
  2. Setup Python 3.11
  3. Install requirements
  4. Run `python -m pipeline.post_replies`
  5. Commit updated `replied_tweets.json` (if changed)
  6. Push

## Safety Guardrails

| Guardrail | Implementation |
|---|---|
| Hard reply cap | Max 10 replies per run |
| Rate limiting | 60-second sleep between replies |
| No double-replying | `replied_tweets.json` tracks all replied tweet IDs |
| Content filter (inbound) | Skip tweets with profanity/slurs |
| Content filter (outbound) | Reject AI replies containing promotional language |
| Dry-run mode | `X_DRY_RUN=true` logs everything without posting |
| Graceful failure | AI generation failure = skip tweet, don't crash |
| Recency gate | Only reply to tweets < 6 hours old |

## Configuration Constants

All defined at top of `post_replies.py`:

```python
MAX_REPLIES_PER_RUN = 10
MIN_LIKES = 5
MIN_RETWEETS = 3
MAX_TWEET_AGE_HOURS = 6
REPLY_DELAY_SECONDS = 60
REPLIED_TWEETS_RETENTION_DAYS = 7
```

## Dependencies

- `tweepy>=4.14.0` (already in requirements.txt)
- `openai>=1.40.0` (already in requirements.txt)
- No new dependencies needed
