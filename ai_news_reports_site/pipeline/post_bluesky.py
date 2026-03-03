"""
post_bluesky.py — Post today's TL;DR News digest to Bluesky.

Reads the latest daily report JSON, formats a short post, and publishes it
via the AT Protocol HTTP API using only Python stdlib (no extra dependencies).

Required environment variables:
  BSKY_IDENTIFIER   — Bluesky handle, e.g. yourhandle.bsky.social
  BSKY_APP_PASSWORD — App password from Settings > App Passwords
  SITE_URL          — Deployed site URL, e.g. https://your-domain.com
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


BSKY_HOST = "https://bsky.social"
TZ = "America/Denver"
MAX_POST_CHARS = 290  # Bluesky limit is 300; leave buffer


def _api(endpoint: str, payload: dict, token: str | None = None) -> dict:
    url = f"{BSKY_HOST}/xrpc/{endpoint}"
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _get_session(identifier: str, app_password: str) -> dict:
    return _api("com.atproto.server.createSession", {
        "identifier": identifier,
        "password": app_password,
    })


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


def _build_post(report: dict, site_url: str) -> tuple[str, str]:
    """Returns (post_text, report_url)."""
    date = report.get("date", datetime.now(ZoneInfo(TZ)).date().isoformat())
    categories = report.get("categories", {})

    # Collect top themes from each category (first theme only)
    highlights = []
    for cat_key in ["world", "technology", "business"]:
        cat = categories.get(cat_key, {})
        themes = cat.get("ai_report", {}).get("key_themes", [])
        if themes:
            highlights.append(themes[0])

    report_url = f"{site_url.rstrip('/')}/news/reports.html?date={date}"

    lines = [f"TL;DR News — {date}"]
    for h in highlights[:3]:
        lines.append(f"• {h}")
    lines.append(report_url)

    post = "\n".join(lines)
    if len(post) > MAX_POST_CHARS:
        # Trim highlights to fit
        lines = [f"TL;DR News — {date}", highlights[0] if highlights else "", report_url]
        post = "\n".join(l for l in lines if l)

    return post[:MAX_POST_CHARS], report_url


def _make_facets(text: str, url: str) -> list:
    """Create a link facet for the URL so Bluesky renders it as a hyperlink."""
    encoded = text.encode("utf-8")
    start = encoded.find(url.encode("utf-8"))
    if start == -1:
        return []
    return [{
        "index": {"byteStart": start, "byteEnd": start + len(url.encode("utf-8"))},
        "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}],
    }]


def main() -> int:
    identifier = os.environ.get("BSKY_IDENTIFIER", "").strip()
    app_password = os.environ.get("BSKY_APP_PASSWORD", "").strip()
    site_url = os.environ.get("SITE_URL", "https://YOUR_DOMAIN").strip()

    if not identifier or not app_password:
        print("BSKY_IDENTIFIER or BSKY_APP_PASSWORD not set — skipping Bluesky post.")
        return 0

    site_root = Path(__file__).resolve().parents[1]
    report = _load_latest_report(site_root)
    if not report:
        print("No report found — skipping Bluesky post.", file=sys.stderr)
        return 1

    post_text, report_url = _build_post(report, site_url)
    print(f"Posting to Bluesky:\n{post_text}")

    try:
        session = _get_session(identifier, app_password)
        token = session["accessJwt"]
        did = session["did"]

        record = {
            "$type": "app.bsky.feed.post",
            "text": post_text,
            "facets": _make_facets(post_text, report_url),
            "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "langs": ["en"],
        }
        result = _api("com.atproto.repo.createRecord", {
            "repo": did,
            "collection": "app.bsky.feed.post",
            "record": record,
        }, token=token)
        print(f"Posted: {result.get('uri', 'ok')}")
        return 0
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"Bluesky API error {e.code}: {body}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Bluesky post failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
