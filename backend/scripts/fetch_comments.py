"""
Fetch a sample of public comments from regulations.gov for docket FTC-2023-0007.

Saves to data/raw/regulations_comments_sample.json

Requirements:
  - REGULATIONS_API_KEY in .env or environment
  - Get a free key at: https://api.data.gov/signup/

Usage:
  python scripts/fetch_comments.py

Rate limit: 1,000 requests/hour with free key.
This script makes ~50+ requests for a 50-comment sample (one detail call per comment).
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

REGULATIONS_API_BASE = "https://api.regulations.gov/v4"
DOCKET_ID = "FTC-2023-0007"
SAMPLE_SIZE = 50
MIN_TEXT_LENGTH = 100  # skip form letters and very short comments

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
OUTPUT_FILE = DATA_DIR / "regulations_comments_sample.json"


def get_api_key() -> str:
    key = os.getenv("REGULATIONS_API_KEY", "").strip()
    if not key:
        print("ERROR: REGULATIONS_API_KEY not set.")
        print("Get a free key at https://api.data.gov/signup/")
        print("Then add it to backend/.env:")
        print("  REGULATIONS_API_KEY=your_key_here")
        sys.exit(1)
    return key


def fetch_comment_list(client: httpx.Client, api_key: str, page_size: int = 25) -> list[dict]:
    """Fetch the first page of comments for the docket."""
    params = {
        "filter[docketId]": DOCKET_ID,
        "page[size]": page_size,
        "page[number]": 1,
        "sort": "-postedDate",  # newest first for freshness
        "api_key": api_key,
    }
    url = f"{REGULATIONS_API_BASE}/comments"
    response = client.get(url, params=params, timeout=30)

    if response.status_code == 403:
        data = response.json()
        print(f"ERROR: API key rejected: {data.get('error', {}).get('message', 'unknown')}")
        sys.exit(1)

    response.raise_for_status()
    return response.json()


def fetch_comment_detail(client: httpx.Client, api_key: str, comment_id: str) -> "dict | None":
    """Fetch full text and metadata for a single comment."""
    url = f"{REGULATIONS_API_BASE}/comments/{comment_id}"
    params = {"api_key": api_key}

    response = client.get(url, params=params, timeout=30)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def parse_comment(detail: dict) -> dict | None:
    """Extract the fields we care about from the API response."""
    attrs = detail.get("data", {}).get("attributes", {})
    comment_id = detail.get("data", {}).get("id", "")

    text = (attrs.get("comment") or "").strip()
    if len(text) < MIN_TEXT_LENGTH:
        return None  # skip blanks and one-liners

    # Determine submitter type from category field
    submitter_type = attrs.get("submitterType") or attrs.get("category") or "Unknown"

    source_url = (
        f"https://www.regulations.gov/comment/{comment_id}"
        if comment_id
        else ""
    )

    return {
        "comment_id": comment_id,
        "submission_date": attrs.get("postedDate") or attrs.get("receiveDate", ""),
        "submitter_type": submitter_type,
        "organization": attrs.get("organization", ""),
        "comment_text": text,
        "source_url": source_url,
    }


def main():
    api_key = get_api_key()

    print("Regulations.gov Comment Sampling")
    print(f"Docket: {DOCKET_ID}")
    print(f"Target sample size: {SAMPLE_SIZE}")
    print(f"Output: {OUTPUT_FILE}")

    with httpx.Client(follow_redirects=True) as client:
        print("\n→ Fetching comment list...")
        # Fetch 2× the target so we have room to filter short/empty comments
        list_response = fetch_comment_list(client, api_key, page_size=100)

        meta = list_response.get("meta", {})
        total_comments = meta.get("totalElements", "unknown")
        print(f"  Total comments in docket: {total_comments:,}" if isinstance(total_comments, int) else f"  Total comments: {total_comments}")

        items = list_response.get("data", [])
        print(f"  Retrieved {len(items)} comment stubs from first page")

        comments: list[dict] = []
        skipped = 0

        for i, item in enumerate(items):
            if len(comments) >= SAMPLE_SIZE:
                break

            comment_id = item.get("id", "")
            if not comment_id:
                continue

            print(f"  → [{i+1}/{len(items)}] Fetching detail for {comment_id}...", end="", flush=True)
            detail = fetch_comment_detail(client, api_key, comment_id)

            if detail is None:
                print(" (not found)")
                skipped += 1
                continue

            parsed = parse_comment(detail)
            if parsed is None:
                print(" (skipped: too short)")
                skipped += 1
                continue

            comments.append(parsed)
            text_preview = parsed["comment_text"][:60].replace("\n", " ")
            print(f" ✓  \"{text_preview}...\"")

            # Be polite to the API — stay well under rate limits
            time.sleep(0.2)

    print(f"\n  Collected {len(comments)} comments ({skipped} skipped)")

    output = {
        "docket_id": DOCKET_ID,
        "total_comments_in_docket": total_comments,
        "sample_size": len(comments),
        "sample_note": (
            "First page sorted by newest, filtered to comments >= "
            f"{MIN_TEXT_LENGTH} characters. Not a random sample."
        ),
        "comments": comments,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"\n✓ Saved {OUTPUT_FILE.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
