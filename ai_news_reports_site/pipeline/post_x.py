"""
post_x.py — Post today's TL;DR News digest to X (Twitter).

Uses X API v2 with OAuth 1.0a. No extra dependencies — stdlib only.

Required environment variables:
  X_API_KEY       — Consumer Key (from developer.twitter.com > Your App > Keys)
  X_API_SECRET    — Consumer Secret
  X_ACCESS_TOKEN  — Access Token  (your account; app needs Read+Write permission)
  X_ACCESS_SECRET — Access Token Secret
  SITE_URL        — Deployed site URL, e.g. https://your-domain.com

The X free-tier API allows up to 1,500 posts/month — well above one post/day.
The app must have "Read and Write" permissions set in the developer portal before
generating the access token, otherwise the token will only have read access.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


X_TWEET_URL = "https://api.twitter.com/2/tweets"
TZ = "America/Denver"
MAX_TWEET_CHARS = 275  # X hard limit is 280; leave a small buffer


# ── OAuth 1.0a ────────────────────────────────────────────────────────────────

def _pct(s: str) -> str:
    """Percent-encode per RFC 3986 (X requires this exact encoding)."""
    return urllib.parse.quote(str(s), safe="")


def _oauth_header(
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    access_secret: str,
) -> str:
    """Build an OAuth 1.0a Authorization header for a JSON-body POST request."""
    oauth = {
        "oauth_consumer_key":     consumer_key,
        "oauth_nonce":            uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        str(int(time.time())),
        "oauth_token":            access_token,
        "oauth_version":          "1.0",
    }

    # Signature base: only OAuth params (JSON body is not included)
    param_string = "&".join(
        f"{_pct(k)}={_pct(v)}" for k, v in sorted(oauth.items())
    )
    base_string = "&".join([
        _pct(method.upper()),
        _pct(url),
        _pct(param_string),
    ])

    signing_key = f"{_pct(consumer_secret)}&{_pct(access_secret)}"
    sig = base64.b64encode(
        hmac.new(
            signing_key.encode("ascii"),
            base_string.encode("ascii"),
            hashlib.sha1,
        ).digest()
    ).decode("ascii")

    oauth["oauth_signature"] = sig
    header = ", ".join(
        f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth.items())
    )
    return f"OAuth {header}"


# ── Report helpers ────────────────────────────────────────────────────────────

def _load_latest_report(site_root: Path) -> dict | None:
    index_path = site_root / "news" / "data" / "reports_index.json"
    if not index_path.exists():
        return None
    index = json.loads(index_path.read_text(encoding="utf-8"))
    latest = index.get("latest_date")
    if not latest:
        return None
    report_path = site_root / "news" / "data" / "reports" / f"{latest}.json"
    if not report_path.exists():
        return None
    return json.loads(report_path.read_text(encoding="utf-8"))


def _build_tweet(report: dict, site_url: str) -> str:
    date = report.get("date", datetime.now(ZoneInfo(TZ)).date().isoformat())
    categories = report.get("categories", {})

    highlights = []
    for cat_key in ["world", "technology", "business"]:
        themes = categories.get(cat_key, {}).get("ai_report", {}).get("key_themes", [])
        if themes:
            highlights.append(themes[0])

    report_url = f"{site_url.rstrip('/')}/news/reports.html?date={date}"

    lines = [f"TL;DR News — {date}"]
    for h in highlights[:3]:
        lines.append(f"• {h}")
    lines.append(report_url)

    tweet = "\n".join(lines)
    if len(tweet) > MAX_TWEET_CHARS:
        # Fallback: just date + first highlight + URL
        tweet = "\n".join(filter(None, [
            f"TL;DR News — {date}",
            highlights[0] if highlights else "",
            report_url,
        ]))

    return tweet[:MAX_TWEET_CHARS]


# ── Post ──────────────────────────────────────────────────────────────────────

def _post_tweet(text: str, auth: str) -> dict:
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        X_TWEET_URL,
        data=body,
        headers={
            "Authorization": auth,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def main() -> int:
    api_key      = os.environ.get("X_API_KEY",       "").strip()
    api_secret   = os.environ.get("X_API_SECRET",    "").strip()
    access_token = os.environ.get("X_ACCESS_TOKEN",  "").strip()
    access_secret= os.environ.get("X_ACCESS_SECRET", "").strip()
    site_url     = os.environ.get("SITE_URL", "https://YOUR_DOMAIN").strip()

    if not all([api_key, api_secret, access_token, access_secret]):
        print("X credentials not fully set — skipping post.")
        return 0

    site_root = Path(__file__).resolve().parents[1]
    report = _load_latest_report(site_root)
    if not report:
        print("No report found — skipping X post.", file=sys.stderr)
        return 1

    tweet = _build_tweet(report, site_url)
    print(f"Posting to X:\n{tweet}")

    try:
        auth = _oauth_header(
            "POST", X_TWEET_URL,
            api_key, api_secret, access_token, access_secret,
        )
        result = _post_tweet(tweet, auth)
        tweet_id = result.get("data", {}).get("id", "")
        url = f"https://x.com/i/web/status/{tweet_id}" if tweet_id else "ok"
        print(f"Posted: {url}")
        return 0
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"X API error {e.code}: {body}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"X post failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
