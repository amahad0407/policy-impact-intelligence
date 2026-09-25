"""
analyze_comparison.py

Extracts key sections from the downloaded Federal Register documents for the
proposed (2023-00414) and final (2024-09171) FTC Non-Compete Clause Rule and
sends them to Azure AI Foundry (GPT-4o) for a structured comparison.

Saves to: data/processed/comparison_analysis.json

Usage:
    cd backend && source venv/bin/activate
    python scripts/analyze_comparison.py
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

RAW       = _root / "data" / "raw"
PROCESSED = _root / "data" / "processed"
OUTPUT    = PROCESSED / "comparison_analysis.json"

MAX_CHARS_PER_DOC = 14_000
MAX_OUTPUT_TOKENS = 4000

# Headings whose text is highest-value for comparing rule language
COMPARE_KEYWORDS = [
    "summary",
    "overview of the proposed",
    "summary of the final",
    "part 910",
    "910.1", "910.2",
    "definition",
    "unfair method",
    "rescission",
    "notice requirement",
    "senior executive",
    "worker",
    "employer",
    "scope",
    "effective date",
    "exempt",
    "enforcement",
    "provision",
]


def check_env() -> tuple[str, str, str]:
    ep  = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
    key = os.getenv("AZURE_OPENAI_API_KEY",  "").strip()
    dep = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o").strip()
    bad = [n for n, v in [("AZURE_OPENAI_ENDPOINT", ep), ("AZURE_OPENAI_API_KEY", key)]
           if not v or "YOUR_RESOURCE" in v or v == "your_key_here"]
    if bad:
        print("❌  Missing credentials:", ", ".join(bad)); sys.exit(1)
    return ep, key, dep


def call_with_retry(client: OpenAI, **kwargs) -> object:
    for attempt, delay in enumerate([10, 20, 40, None]):
        try:
            return client.responses.create(**kwargs)
        except RateLimitError as e:
            if delay is None: raise
            hdrs = getattr(getattr(e, "response", None), "headers", {})
            ram  = hdrs.get("retry-after-ms")
            ras  = hdrs.get("retry-after")
            wait = max(float(delay),
                       int(ram) / 1000 + 1 if ram else
                       float(ras) + 1   if ras else float(delay))
            print(f"  ⚠  429 attempt {attempt+1}/3, waiting {wait:.0f}s…")
            time.sleep(wait)


def load_doc(filename: str) -> dict:
    p = RAW / filename
    if not p.exists():
        print(f"❌  {filename} not found. Run fetch_federal_register.py first.")
        sys.exit(1)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def extract_for_comparison(doc: dict, max_chars: int) -> str:
    """Return the sections most useful for a side-by-side comparison, capped at max_chars."""
    sections = doc.get("sections", [])

    # Score each section: 0 = high relevance, 1 = lower
    scored = []
    for i, s in enumerate(sections):
        h = s.get("heading", "").lower()
        t = s.get("text", "").strip()
        if not t:
            continue
        priority = 0 if any(kw in h for kw in COMPARE_KEYWORDS) else 1
        scored.append((priority, i, s))

    scored.sort(key=lambda x: (x[0], x[1]))

    parts: list[str] = []
    total = 0
    for _, _, s in scored:
        chunk = f"### {s['heading']}\n{s['text'][:2000]}"
        if total + len(chunk) > max_chars:
            break
        parts.append(chunk)
        total += len(chunk)

    return "\n\n".join(parts)


def build_prompt(prop_extract: str, final_extract: str,
                 prop_meta: dict, final_meta: dict) -> str:
    return f"""You are a professional government policy analyst comparing two versions of a
federal regulation. Your task is to produce a structured, evidence-grounded comparison.

CRITICAL RULES:
- Ground every comparison in the text provided. Do not invent differences or similarities.
- Use neutral language: "the final rule changed…", "the final rule removed…", not "improved" or "worsened".
- Do not recommend which version is better.
- Clearly label which document each quote or paraphrase comes from.
- If you cannot confidently compare something from the provided text, say so.
- Keep source attribution precise (e.g. "Final Rule, § 910.1" or "Proposed Rule, Section I").

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCUMENT A — PROPOSED RULE
Document number: {prop_meta['document_number']}
Published: {prop_meta['publication_date']}
URL: {prop_meta['source_url']}

{prop_extract}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCUMENT B — FINAL RULE
Document number: {final_meta['document_number']}
Published: {final_meta['publication_date']}
URL: {final_meta['source_url']}

{final_extract}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return ONLY valid JSON — no markdown. Match this exact schema:

{{
  "summary": "<3-5 sentence neutral summary of the most important differences between the two versions>",
  "key_changes": [
    {{
      "topic": "<policy topic, e.g. Scope, Senior Executives, Notice Requirement>",
      "proposed": "<what the proposed rule said, with source reference>",
      "final": "<what the final rule says, with source reference>",
      "change_description": "<neutral description of what changed, starting with 'The final rule...'>"
    }}
  ],
  "unchanged_elements": [
    "<something that remained consistent between proposed and final, with source>"
  ],
  "definitions": [
    {{
      "term": "<defined term>",
      "proposed_definition": "<definition from proposed rule, or 'Not explicitly defined'>",
      "final_definition": "<definition from final rule, or 'Not explicitly defined'>",
      "changed": true
    }}
  ],
  "timeline": [
    {{
      "date": "<date>",
      "event": "<what happened>",
      "document": "<Proposed Rule | Final Rule | Other>"
    }}
  ],
  "limitations": [
    "<honest limitation of this comparison, e.g. partial text only, section not available>"
  ],
  "sources": [
    {{
      "label": "<e.g. Proposed Rule>",
      "document_number": "<document number>",
      "publication_date": "<date>",
      "url": "<url>"
    }}
  ]
}}"""


def main() -> None:
    print("Policy Comparison Pipeline")
    print("Proposed Rule + Final Rule → Azure AI Foundry → comparison_analysis.json")
    print()

    endpoint, api_key, deployment = check_env()
    print(f"✓ Foundry: {endpoint}  deployment={deployment}")

    proposed = load_doc("federal_register_proposed_rule.json")
    final    = load_doc("federal_register_final_rule.json")
    print(f"\n→ Proposed Rule: {proposed['document_number']} · {proposed['publication_date']} · {len(proposed['sections'])} sections")
    print(f"→ Final Rule:    {final['document_number']}   · {final['publication_date']} · {len(final['sections'])} sections")

    print(f"\n→ Extracting comparison sections (max {MAX_CHARS_PER_DOC:,} chars each)…")
    prop_extract  = extract_for_comparison(proposed, MAX_CHARS_PER_DOC)
    final_extract = extract_for_comparison(final,    MAX_CHARS_PER_DOC)
    print(f"  Proposed extract: {len(prop_extract):,} chars")
    print(f"  Final extract:    {len(final_extract):,} chars")

    prop_meta  = {k: proposed[k] for k in ("document_number", "publication_date", "source_url")}
    final_meta = {k: final[k]    for k in ("document_number", "publication_date", "source_url")}

    prompt = build_prompt(prop_extract, final_extract, prop_meta, final_meta)
    print(f"\n→ Prompt size: ~{len(prompt)//4:,} tokens (estimated)")

    client = OpenAI(base_url=f"{endpoint}/openai/v1/", api_key=api_key)
    print(f"\n→ Sending to Foundry ({deployment})…")

    try:
        response = call_with_retry(
            client,
            model=deployment,
            instructions=(
                "You are a professional government policy analyst. "
                "You compare regulatory documents objectively, without recommending "
                "any policy outcome. You cite sources precisely. "
                "You output only valid JSON."
            ),
            input=prompt,
            text={"format": {"type": "json_object"}},
            temperature=0.1,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
    except RateLimitError as e:
        print(f"\n❌  Rate limit persisted: {e}"); sys.exit(1)
    except Exception as e:
        print(f"\n❌  Foundry failed: {e}"); sys.exit(1)

    usage = response.usage
    print(f"  ✓ Received  ({usage.input_tokens:,} in / {usage.output_tokens:,} out)")

    try:
        result = json.loads(response.output_text)
    except json.JSONDecodeError as e:
        print(f"❌  Invalid JSON: {e}\n{response.output_text[:300]}"); sys.exit(1)

    result["_metadata"] = {
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "deployment":      deployment,
        "input_tokens":    usage.input_tokens,
        "output_tokens":   usage.output_tokens,
        "proposed_doc":    proposed["document_number"],
        "final_doc":       final["document_number"],
        "disclaimer":      (
            "This comparison is AI-generated from partial document extracts. "
            "It does not substitute for a legal review of the full regulatory text."
        ),
    }

    PROCESSED.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    kb = OUTPUT.stat().st_size / 1024
    print(f"\n✓ Saved {OUTPUT.name} ({kb:.1f} KB)")
    print("\n─── Preview ──────────────────────────────────────────────")
    print(f"  key_changes:        {len(result.get('key_changes',[]))}")
    print(f"  unchanged_elements: {len(result.get('unchanged_elements',[]))}")
    print(f"  definitions:        {len(result.get('definitions',[]))}")
    print(f"  timeline:           {len(result.get('timeline',[]))}")
    print(f"  limitations:        {len(result.get('limitations',[]))}")
    print("──────────────────────────────────────────────────────────")
    print("\n✓ Comparison complete.")


if __name__ == "__main__":
    main()
