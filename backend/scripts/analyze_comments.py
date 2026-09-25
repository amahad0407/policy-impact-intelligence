"""
analyze_comments.py

Loads the regulations_comments_sample.json file and sends the comments
to Azure AI Foundry (GPT-4o) for thematic analysis.

Saves structured analysis to data/processed/comments_analysis.json.

Usage:
    cd backend
    source venv/bin/activate
    python scripts/analyze_comments.py

Requires:
    - data/raw/regulations_comments_sample.json  (run fetch_comments.py first)
    - AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME in .env
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

_here = Path(__file__).resolve().parent.parent
_root = _here.parent
load_dotenv(_here / ".env")
load_dotenv(_root / ".env")

DATA_RAW       = _root / "data" / "raw"
DATA_PROCESSED = _root / "data" / "processed"
INPUT_FILE     = DATA_RAW / "regulations_comments_sample.json"
OUTPUT_FILE    = DATA_PROCESSED / "comments_analysis.json"

MAX_COMMENT_CHARS = 500   # cap per comment to control token budget
MAX_OUTPUT_TOKENS = 2500


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

def check_env() -> tuple[str, str, str]:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
    api_key  = os.getenv("AZURE_OPENAI_API_KEY",  "").strip()
    deploy   = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o").strip()
    missing  = []
    if not endpoint or "YOUR_RESOURCE" in endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not api_key or api_key == "your_key_here":
        missing.append("AZURE_OPENAI_API_KEY")
    if missing:
        print("❌  Azure credentials not configured:", ", ".join(missing))
        sys.exit(1)
    return endpoint, api_key, deploy


# ---------------------------------------------------------------------------
# Rate-limit retry (same pattern as analyze_policy.py)
# ---------------------------------------------------------------------------

def call_with_retry(client: OpenAI, **kwargs) -> object:
    base_delays = [10, 20, 40]
    for attempt, base_delay in enumerate(base_delays + [None]):
        try:
            return client.responses.create(**kwargs)
        except RateLimitError as e:
            if base_delay is None:
                raise
            delay = float(base_delay)
            headers = getattr(getattr(e, "response", None), "headers", {})
            if headers:
                for h in ("retry-after-ms", "retry-after",
                          "x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens"):
                    val = headers.get(h)
                    if val:
                        print(f"    {h}: {val}")
                ram = headers.get("retry-after-ms")
                ras = headers.get("retry-after")
                if ram:
                    delay = max(delay, int(ram) / 1000 + 1)
                elif ras:
                    delay = max(delay, float(ras) + 1)
            print(f"  ⚠  429 rate limit (attempt {attempt+1}/3). Waiting {delay:.0f}s...")
            time.sleep(delay)


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

def format_comment(c: dict, index: int) -> str:
    text = c["comment_text"][:MAX_COMMENT_CHARS]
    if len(c["comment_text"]) > MAX_COMMENT_CHARS:
        text += "…"
    org   = (c.get("organization") or "").strip()
    stype = c.get("submitter_type", "Unknown")
    label = f"{org} ({stype})" if org else stype
    return f"[{index+1}] ID:{c['comment_id']} | {label}\n{text}"


def build_prompt(comments: list[dict], meta: dict) -> str:
    formatted = "\n\n".join(format_comment(c, i) for i, c in enumerate(comments))
    total = meta.get("total_comments_in_docket", "unknown")

    return f"""You are an expert policy analyst reviewing public comments on a federal rulemaking.

DOCKET: FTC-2023-0007 — Non-Compete Clause Rule
SAMPLE: {len(comments)} comments out of approximately {total} total submissions.

CRITICAL INSTRUCTIONS:
- Do NOT say whether the rule is good or bad.
- Do NOT make policy recommendations.
- Identify recurring themes and viewpoints purely from what commenters wrote.
- Every theme and viewpoint MUST cite at least one comment ID as evidence.
- Use the exact commenter's words when quoting (mark with comment ID).
- Preserve minority and dissenting viewpoints — do not flatten disagreement.
- This is a non-random sample; note limitations honestly.
- Use "source_type": "opinion" for all commenter content.

PUBLIC COMMENTS:
{formatted}

---

Return ONLY valid JSON. No markdown fences. Match this exact schema:

{{
  "summary": "<2-3 sentence neutral summary of what commenters focused on>",
  "themes": [
    {{
      "theme": "<short theme name>",
      "description": "<what commenters said about this theme>",
      "comment_count": <number of comments touching this theme>,
      "evidence": [
        {{
          "comment_id": "<ID from the comment header>",
          "excerpt": "<direct quote or close paraphrase>",
          "source_url": "<leave empty string if not available>"
        }}
      ]
    }}
  ],
  "viewpoints": [
    {{
      "label": "<viewpoint label, e.g. Supportive / Opposed / Conditional>",
      "description": "<what this group of commenters argued>",
      "comment_count": <estimated number>,
      "evidence": [
        {{
          "comment_id": "<ID>",
          "excerpt": "<quote>",
          "source_url": ""
        }}
      ]
    }}
  ],
  "affected_groups": [
    "<group mentioned by commenters>"
  ],
  "limitations": [
    "<honest limitation of this analysis, e.g. sample size, recency bias, etc.>"
  ]
}}"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Comments Analysis Pipeline")
    print("Regulations.gov sample → Azure AI Foundry → structured JSON")
    print()

    endpoint, api_key, deployment = check_env()
    print(f"✓ Foundry endpoint: {endpoint}")
    print(f"  Deployment: {deployment}")

    # Load comments
    if not INPUT_FILE.exists():
        print(f"\n❌  {INPUT_FILE.name} not found.")
        print("   Run: python scripts/fetch_comments.py")
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    comments = raw.get("comments", [])
    if not comments:
        print("❌  No comments in input file.")
        sys.exit(1)

    print(f"\n→ Loaded {len(comments)} comments from {INPUT_FILE.name}")
    print(f"  Docket total: {raw.get('total_comments_in_docket', 'unknown')}")

    # Build prompt
    prompt = build_prompt(comments, raw)
    print(f"\n→ Prompt size: ~{len(prompt)//4:,} tokens (estimated)")

    # Call Foundry
    print(f"\n→ Sending to Foundry ({deployment})...")
    client = OpenAI(
        base_url=f"{endpoint}/openai/v1/",
        api_key=api_key,
    )

    try:
        response = call_with_retry(
            client,
            model=deployment,
            instructions=(
                "You are a professional government policy analyst. "
                "You analyze public comments on federal rulemakings. "
                "You are neutral, evidence-based, and clearly label all content as public opinion. "
                "You output only valid JSON as instructed."
            ),
            input=prompt,
            text={"format": {"type": "json_object"}},
            temperature=0.1,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
    except RateLimitError as e:
        print(f"\n❌  Rate limit persisted after 3 retries: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌  Foundry API call failed: {e}")
        sys.exit(1)

    raw_json = response.output_text
    usage    = response.usage
    print(f"  ✓ Response received")
    print(f"    Input tokens:  {usage.input_tokens:,}")
    print(f"    Output tokens: {usage.output_tokens:,}")

    # Parse
    try:
        analysis = json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f"❌  Model returned invalid JSON: {e}")
        print(raw_json[:400])
        sys.exit(1)

    # Enrich evidence with real source URLs from the fetched comments
    url_map = {c["comment_id"]: c.get("source_url", "") for c in comments}
    for section in ("themes", "viewpoints"):
        for item in analysis.get(section, []):
            for ev in item.get("evidence", []):
                cid = ev.get("comment_id", "")
                if cid in url_map:
                    ev["source_url"] = url_map[cid]

    # Attach metadata
    analysis["_metadata"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deployment": deployment,
        "sample_size": len(comments),
        "total_comments_in_docket": raw.get("total_comments_in_docket"),
        "sample_note": raw.get("sample_note", ""),
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
    }

    # Save
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"\n✓ Saved {OUTPUT_FILE.name} ({size_kb:.1f} KB)")

    print("\n─── Output preview ───────────────────────────────────")
    print(f"  summary:         {len(analysis.get('summary', ''))} chars")
    print(f"  themes:          {len(analysis.get('themes', []))} items")
    print(f"  viewpoints:      {len(analysis.get('viewpoints', []))} items")
    print(f"  affected_groups: {len(analysis.get('affected_groups', []))} items")
    print(f"  limitations:     {len(analysis.get('limitations', []))} items")
    print("──────────────────────────────────────────────────────")
    print("\n✓ Analysis complete.")


if __name__ == "__main__":
    main()
