"""
fetch_news.py

Fetches relevant news articles about the FTC Non-Compete Clause Rule from the
Google News RSS feed (no API key required) and saves raw metadata to:
    data/raw/news_articles.json

Uses only httpx (already installed) and Python's built-in xml.etree.

To swap to Bing News Search API later, replace the fetch_from_rss() call
with a Bing News request using BING_NEWS_API_KEY from .env.

Usage:
    cd backend
    source venv/bin/activate
    python scripts/fetch_news.py
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

_here = Path(__file__).resolve().parent.parent
_root = _here.parent
load_dotenv(_here / ".env")
load_dotenv(_root / ".env")

DATA_DIR    = _root / "data" / "raw"
OUTPUT_FILE = DATA_DIR / "news_articles.json"

TARGET_ARTICLES = 15

QUERIES = [
    "FTC non-compete rule ban 2024",
    "non-compete clause federal rule court",
    "FTC Ryan LLC non-compete ruling",
]

GNEWS_BASE = "https://news.google.com/rss/search"


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def parse_rfc2822_date(date_str: str) -> str:
    """Parse RFC-2822 date to ISO format. Returns original string on failure."""
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str).isoformat()
    except Exception:
        return date_str


def fetch_from_rss(client: httpx.Client, query: str, max_results: int = 10) -> list[dict]:
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    url = f"{GNEWS_BASE}?{urllib.parse.urlencode(params)}"
    print(f"  → Querying: {query!r}")
    try:
        resp = client.get(url, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"    ⚠  Request failed: {e}")
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        print(f"    ⚠  XML parse error: {e}")
        return []

    articles = []
    for item in root.findall(".//item")[:max_results]:
        title   = strip_html(item.findtext("title", ""))
        link    = item.findtext("link", "")
        pub_date = parse_rfc2822_date(item.findtext("pubDate", ""))
        desc    = strip_html(item.findtext("description", ""))

        source_el   = item.find("source")
        publication = source_el.text.strip() if source_el is not None and source_el.text else ""
        source_url  = source_el.get("url", "") if source_el is not None else ""

        if not title or not link:
            continue

        articles.append({
            "headline":    title,
            "publication": publication,
            "source_url":  source_url,
            "date":        pub_date,
            "url":         link,
            "description": desc[:500],
        })

    print(f"    Retrieved {len(articles)} articles")
    return articles


def deduplicate(articles: list[dict]) -> list[dict]:
    """Remove duplicates by normalised headline."""
    seen: set[str] = set()
    unique = []
    for a in articles:
        key = re.sub(r"\W+", " ", a["headline"].lower()).strip()[:80]
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


def main() -> None:
    print("News Article Fetch")
    print(f"Source: Google News RSS (no API key required)")
    print(f"Target: {TARGET_ARTICLES} articles")
    print(f"Output: {OUTPUT_FILE}")
    print()

    all_articles: list[dict] = []

    with httpx.Client(follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
        for query in QUERIES:
            results = fetch_from_rss(client, query, max_results=8)
            all_articles.extend(results)
            time.sleep(0.5)   # polite delay between queries

    # Deduplicate and limit
    unique = deduplicate(all_articles)
    # Sort newest first (ISO strings sort lexicographically correctly for dates)
    unique.sort(key=lambda a: a.get("date", ""), reverse=True)
    final = unique[:TARGET_ARTICLES]

    print(f"\n  {len(all_articles)} total → {len(unique)} unique → {len(final)} kept")

    if not final:
        print("\n⚠  No articles retrieved. Check network connectivity.")
        return

    output = {
        "query_terms":    QUERIES,
        "article_count":  len(final),
        "articles":       final,
        "fetched_at":     datetime.now(timezone.utc).isoformat(),
        "source_note":    (
            "Articles fetched from Google News RSS feed. "
            "Sample may not represent full media coverage."
        ),
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"\n✓ Saved {OUTPUT_FILE.name} ({size_kb:.1f} KB)")
    print(f"\nSample headlines:")
    for a in final[:5]:
        print(f"  [{a['publication']}] {a['headline'][:80]}")


if __name__ == "__main__":
    main()
