# X Posting Agent — Design

**Date:** 2026-03-08
**Status:** Approved

## Overview

Add automated daily X (Twitter) posting to the TLDR-NEWS pipeline. Each of the 5 news categories gets its own tweet, staggered 20 minutes apart, with an AI-generated emotion-sparking hook line, sentiment score, and link to tldrnews.info.

## Architecture

Two new components plus a new workflow:

1. **`TweetWriterAgent`** (`pipeline/agents/tweet_writer.py`) — runs during the daily pipeline, uses OpenAI to generate a punchy hook line per category, saves tweet texts into the daily report JSON.
2. **`post_tweets.py`** (`pipeline/post_tweets.py`) — lightweight script that reads today's report JSON, picks the tweet for a given category index, and posts it via the X API.
3. **Post workflow** (`.github/workflows/post_tweets.yml`) — 5 cron jobs staggered 20 min apart, each calling `post_tweets.py` with a category index.

## Tweet Format

```
[AI-generated emotion-sparking hook line]

Sentiment: [Positive/Negative/Mixed/Neutral] ([+0.1234])

Read the full breakdown: https://tldrnews.info
```

~200 chars max, well under the 280 limit.

## Data Flow

```
Daily pipeline run (14:10 UTC)
  -> TweetWriterAgent generates 5 tweet texts
  -> Saved in YYYY-MM-DD.json under each category as "tweet_text"

Post workflow (14:30, 14:50, 15:10, 15:30, 15:50 UTC)
  -> post_tweets.py reads report JSON
  -> Posts tweet for category[N] via X API (OAuth 1.0a)
  -> Skips if already posted or tweet_text missing
```

## X API Authentication

- OAuth 1.0a (User Authentication) using 4 credentials stored as GitHub Secrets:
  - `X_API_KEY`, `X_API_SECRET`, `X_CONSUMER_KEY`, `X_CONSUMER_SECRET`
- Python library: `tweepy` (added to `requirements.txt`)

## Graceful Degradation

- If OpenAI fails to generate a hook: falls back to a template using category title + top headline.
- If X API fails: logs error, does not crash the workflow.
- Dry-run mode via `X_DRY_RUN=true` env var: logs tweet text without posting.

## Files Changed/Created

| File | Action |
|---|---|
| `pipeline/agents/tweet_writer.py` | New — AI hook generation |
| `pipeline/post_tweets.py` | New — X API posting script |
| `pipeline/run_daily.py` | Modified — call TweetWriterAgent, save tweet_text |
| `.github/workflows/post_tweets.yml` | New — staggered cron workflow |
| `requirements.txt` | Modified — add `tweepy` |

## Secrets Required

Add to GitHub repo Settings > Secrets and variables > Actions:

- `X_API_KEY`
- `X_API_SECRET`
- `X_CONSUMER_KEY`
- `X_CONSUMER_SECRET`
