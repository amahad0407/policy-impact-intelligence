"""
analyze_briefing.py

Synthesises the three existing processed JSON files into a single structured
analyst briefing using Azure AI Foundry (GPT-4o).

Input  files: data/processed/policy_summary.json
              data/processed/comments_analysis.json
              data/processed/news_analysis.json

Output file:  data/processed/briefing_analysis.json

Usage:
    cd backend && source venv/bin/activate
    python scripts/analyze_briefing.py
"""

from __future__ import annotations

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

PROCESSED   = _root / "data" / "processed"
OUTPUT_FILE = PROCESSED / "briefing_analysis.json"

MAX_OUTPUT_TOKENS = 4000


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

def check_env() -> tuple[str, str, str]:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
    api_key  = os.getenv("AZURE_OPENAI_API_KEY",  "").strip()
    deploy   = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o").strip()
    missing  = [n for n, v in [
        ("AZURE_OPENAI_ENDPOINT", endpoint),
        ("AZURE_OPENAI_API_KEY",  api_key),
    ] if not v or "YOUR_RESOURCE" in v or v == "your_key_here"]
    if missing:
        print("❌  Missing credentials:", ", ".join(missing))
        sys.exit(1)
    return endpoint, api_key, deploy


# ---------------------------------------------------------------------------
# Rate-limit retry
# ---------------------------------------------------------------------------

def call_with_retry(client: OpenAI, **kwargs) -> object:
    delays = [10, 20, 40]
    for attempt, delay in enumerate(delays + [None]):
        try:
            return client.responses.create(**kwargs)
        except RateLimitError as e:
            if delay is None:
                raise
            headers = getattr(getattr(e, "response", None), "headers", {})
            ram = headers.get("retry-after-ms")
            ras = headers.get("retry-after")
            wait = max(float(delay),
                       int(ram) / 1000 + 1 if ram else
                       float(ras) + 1 if ras else float(delay))
            print(f"  ⚠  429 (attempt {attempt+1}/3). Waiting {wait:.0f}s…")
            time.sleep(wait)


# ---------------------------------------------------------------------------
# Load source files
# ---------------------------------------------------------------------------

def load_sources() -> tuple[dict, dict, dict]:
    missing = []
    for f in ("policy_summary.json", "comments_analysis.json", "news_analysis.json"):
        if not (PROCESSED / f).exists():
            missing.append(f)
    if missing:
        print("❌  Missing source files:", ", ".join(missing))
        print("   Run the corresponding pipeline scripts first.")
        sys.exit(1)

    with open(PROCESSED / "policy_summary.json",   encoding="utf-8") as f:
        policy = json.load(f)
    with open(PROCESSED / "comments_analysis.json", encoding="utf-8") as f:
        comments = json.load(f)
    with open(PROCESSED / "news_analysis.json",     encoding="utf-8") as f:
        news = json.load(f)

    return policy, comments, news


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_prompt(policy: dict, comments: dict, news: dict) -> str:

    # ── Policy section ───────────────────────────────────────────────────────
    policy_block = f"""POLICY SUMMARY (source: official Federal Register documents):
{policy.get('policy_summary', '')}

KEY CHANGES:
{chr(10).join(f'- {c}' for c in policy.get('key_changes', []))}

AFFECTED STAKEHOLDERS (from policy):
{chr(10).join(f'- {s["group"]}: {s["description"]} (impact: {s["impact"]})' for s in policy.get('affected_stakeholders', []))}

POLICY UNCERTAINTIES:
{chr(10).join(f'- {u}' for u in policy.get('uncertainty_or_limitations', []))}"""

    # ── Public comments section ───────────────────────────────────────────────
    meta_c = comments.get('_metadata', {})
    themes_txt = "\n".join(
        f'- {t["theme"]} (~{t["comment_count"]} comments): {t["description"][:150]}'
        for t in comments.get('themes', [])
    )
    viewpoints_txt = "\n".join(
        f'- {v["label"]} (~{v["comment_count"]} comments): {v["description"][:150]}'
        for v in comments.get('viewpoints', [])
    )
    comments_block = f"""PUBLIC COMMENTS (source: {meta_c.get('sample_size', '?')} comments from Regulations.gov docket FTC-2023-0007 out of {meta_c.get('total_comments_in_docket', '~20,000')} total):
SUMMARY: {comments.get('summary', '')}

RECURRING THEMES:
{themes_txt}

VIEWPOINTS REPRESENTED:
{viewpoints_txt}

COMMENT LIMITATIONS:
{chr(10).join(f'- {l}' for l in comments.get('limitations', []))}"""

    # ── News section ──────────────────────────────────────────────────────────
    meta_n = news.get('_metadata', {})
    articles_txt = "\n".join(
        f'- [{a.get("source_type","?")}] {a.get("publication","")}: "{a.get("headline","")[:80]}" — {a.get("summary","")[:150]}'
        for a in news.get('articles', [])
    )
    news_block = f"""NEWS COVERAGE (source: {meta_n.get('articles_analyzed', '?')} articles via news search):
SUMMARY: {news.get('summary', '')}

KEY DEVELOPMENTS:
{chr(10).join(f'- {d}' for d in news.get('key_developments', []))}

COVERAGE THEMES: {', '.join(news.get('coverage_themes', []))}

ARTICLES:
{articles_txt}

NEWS LIMITATIONS:
{chr(10).join(f'- {l}' for l in news.get('limitations', []))}"""

    return f"""You are a professional government policy analyst. Your task is to synthesize
the following three evidence sources into a single structured analyst briefing.

CRITICAL INSTRUCTIONS:
- Do NOT recommend whether the policy should be adopted, kept, changed, or repealed.
- Do NOT state your personal view on the policy.
- Clearly attribute every claim to its source: official policy documents, public comments, or news coverage.
- When sources agree, note that explicitly. When they differ or conflict, preserve the conflict.
- Do not present the 50-comment sample as representative of all public opinion.
- Preserve uncertainty — if the evidence is thin, say so.
- Keep the briefing useful for an analyst who must make their own judgment.
- The analyst makes the final decision, not you.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE 1 — OFFICIAL POLICY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{policy_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE 2 — PUBLIC COMMENTS (limited sample)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{comments_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE 3 — NEWS COVERAGE (limited sample)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{news_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY valid JSON — no markdown fences. Match this exact schema:

{{
  "executive_summary": "<3-5 sentence neutral overview of the policy, its current status, and the overall picture from all three sources>",
  "policy_context": "<concise summary of what the rule is and its current legal status>",
  "key_policy_changes": [
    "<specific change from official documents, with source attribution>"
  ],
  "public_feedback": {{
    "summary": "<neutral summary of what commenters focused on, with sample-size caveat>",
    "themes": [
      "<theme name: brief description (source: public comments)>"
    ],
    "viewpoints": [
      {{
        "label": "<viewpoint label>",
        "description": "<what this group argued>",
        "source": "Public comments — FTC-2023-0007 (limited sample)"
      }}
    ]
  }},
  "news_coverage": {{
    "summary": "<neutral summary of media coverage focus>",
    "developments": [
      "<key development with source article reference>"
    ]
  }},
  "stakeholders": [
    {{
      "group": "<stakeholder name>",
      "impact": "<positive | negative | mixed | neutral>",
      "description": "<what the available sources say about this group>",
      "sources": ["<e.g. Official Policy, Public Comments, News Coverage>"]
    }}
  ],
  "areas_of_alignment": [
    "<something multiple sources agree on, with attribution>"
  ],
  "areas_of_difference": [
    "<something where sources present conflicting or different emphases, with attribution>"
  ],
  "uncertainties_and_limitations": [
    "<specific uncertainty or limitation from any source>"
  ],
  "sources": [
    {{
      "label": "<source label>",
      "type": "<official | public_comment | news>",
      "description": "<brief description>",
      "url": "<url if available, else empty string>"
    }}
  ]
}}"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Analyst Briefing Pipeline")
    print("3 processed sources → Azure AI Foundry → briefing_analysis.json")
    print()

    endpoint, api_key, deployment = check_env()
    print(f"✓ Foundry endpoint: {endpoint}")
    print(f"  Deployment: {deployment}")

    policy, comments, news = load_sources()
    print(f"\n→ Sources loaded:")
    print(f"  policy_summary.json      — {len(policy.get('key_changes', []))} key changes, "
          f"{len(policy.get('affected_stakeholders', []))} stakeholders")
    print(f"  comments_analysis.json   — {comments['_metadata'].get('sample_size','?')} comments, "
          f"{len(comments.get('themes', []))} themes")
    print(f"  news_analysis.json       — {news['_metadata'].get('articles_analyzed','?')} articles, "
          f"{len(news.get('key_developments', []))} developments")

    prompt = build_prompt(policy, comments, news)
    print(f"\n→ Prompt size: ~{len(prompt)//4:,} tokens (estimated)")

    client = OpenAI(base_url=f"{endpoint}/openai/v1/", api_key=api_key)
    print(f"\n→ Sending to Foundry ({deployment})…")

    try:
        response = call_with_retry(
            client,
            model=deployment,
            instructions=(
                "You are a professional government policy analyst. "
                "You synthesize multiple evidence sources into neutral, evidence-grounded briefings. "
                "You never recommend a policy outcome. "
                "You preserve uncertainty and conflicting viewpoints. "
                "You output only valid JSON as instructed."
            ),
            input=prompt,
            text={"format": {"type": "json_object"}},
            temperature=0.1,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
    except RateLimitError as e:
        print(f"\n❌  Rate limit persisted after retries: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌  Foundry call failed: {e}")
        sys.exit(1)

    raw_json = response.output_text
    usage    = response.usage
    print(f"  ✓ Response received  ({usage.input_tokens:,} in / {usage.output_tokens:,} out)")

    try:
        briefing = json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f"❌  Invalid JSON: {e}\n{raw_json[:300]}")
        sys.exit(1)

    # Attach source document URLs from policy metadata
    policy_sources = policy.get("_metadata", {}).get("source_documents", [])
    for src in briefing.get("sources", []):
        if src.get("type") == "official" and not src.get("url"):
            for ps in policy_sources:
                if "proposed" in src.get("label", "").lower() and "proposed" in ps["label"].lower():
                    src["url"] = ps["source_url"]
                elif "final" in src.get("label", "").lower() and "final" in ps["label"].lower():
                    src["url"] = ps["source_url"]

    briefing["_metadata"] = {
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "deployment":     deployment,
        "input_tokens":   usage.input_tokens,
        "output_tokens":  usage.output_tokens,
        "sources_used":   ["policy_summary.json", "comments_analysis.json", "news_analysis.json"],
        "disclaimer":     (
            "This briefing is AI-generated from limited data sources. "
            "It is a starting point for analysis, not a legal interpretation. "
            "Human analyst review is required before use in official communications."
        ),
    }

    PROCESSED.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(briefing, f, indent=2, ensure_ascii=False)

    kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"\n✓ Saved {OUTPUT_FILE.name} ({kb:.1f} KB)")

    print("\n─── Preview ─────────────────────────────────────────────")
    for k in ("executive_summary", "key_policy_changes", "areas_of_alignment",
              "areas_of_difference", "uncertainties_and_limitations", "sources"):
        v = briefing.get(k, [])
        count = len(v) if isinstance(v, list) else len(v)
        print(f"  {k:<36} {count if isinstance(v, list) else len(v)} chars/items")
    print("─────────────────────────────────────────────────────────")
    print("\n✓ Briefing complete.")


if __name__ == "__main__":
    main()
