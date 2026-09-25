"""
analyze_policy.py

Loads the two FTC Non-Compete Clause Rule Federal Register JSON files,
extracts key sections, sends them to Azure OpenAI (via AI Foundry), and
saves structured analysis to data/processed/policy_summary.json.

Usage:
    cd backend
    source venv/bin/activate
    python scripts/analyze_policy.py

Required environment variables (in backend/.env or project-root/.env):
    AZURE_OPENAI_ENDPOINT
    AZURE_OPENAI_API_KEY
    AZURE_OPENAI_DEPLOYMENT_NAME
    AZURE_OPENAI_API_VERSION
"""

import json
import os
import sys
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

# Load .env from backend/ directory, then fall back to project root
_here = Path(__file__).resolve().parent.parent          # backend/
_root = _here.parent                                     # project root
load_dotenv(_here / ".env")
load_dotenv(_root / ".env")

DATA_RAW = _root / "data" / "raw"
DATA_PROCESSED = _root / "data" / "processed"
OUTPUT_FILE = DATA_PROCESSED / "policy_summary.json"

# Headings that carry the highest analytical signal
PRIORITY_HEADING_KEYWORDS = [
    "summary", "overview", "abstract",
    "provision", "requirement",
    "definition", "defined",
    "affected", "impact", "worker",
    "employer", "senior executive",
    "key change", "final rule",
    "effective date", "scope",
    "exemption", "exception",
    "enforcement", "penalty",
    "comment", "rationale", "basis",
]

# Max chars to send per document — kept low to stay within 50K TPM rate limit
MAX_CHARS_PER_DOC = 15_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_env() -> tuple[str, str, str]:
    missing = []
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
    api_key  = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    deploy   = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o").strip()

    if not endpoint or "YOUR_RESOURCE" in endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not api_key or api_key == "your_key_here":
        missing.append("AZURE_OPENAI_API_KEY")

    if missing:
        print("\n❌  Azure credentials not configured.")
        print("   Missing or placeholder values for:", ", ".join(missing))
        print()
        print("   Steps to fix:")
        print("   1. Go to Azure portal → Azure AI Foundry → your project")
        print("   2. In your project, go to  Overview  and copy the project endpoint")
        print("   3. Go to  Settings → Keys  and copy the API key")
        print("   4. Create backend/.env:")
        print("        AZURE_OPENAI_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>")
        print("        AZURE_OPENAI_API_KEY=<your-key>")
        print("        AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o")
        sys.exit(1)

    return endpoint, api_key, deploy


def load_rule(filename: str) -> dict:
    path = DATA_RAW / filename
    if not path.exists():
        print(f"❌  File not found: {path}")
        print("   Run  python scripts/fetch_federal_register.py  first.")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_priority_section(heading: str) -> bool:
    h = heading.lower()
    return any(kw in h for kw in PRIORITY_HEADING_KEYWORDS)


def extract_key_sections(doc: dict, max_chars: int) -> str:
    """
    Return a condensed plain-text extract of the document's most
    informative sections, capped at max_chars.
    """
    sections = doc.get("sections", [])
    selected: list[tuple[int, dict]] = []   # (priority, section)

    for i, s in enumerate(sections):
        heading = s.get("heading", "")
        text    = s.get("text", "")
        if not text.strip():
            continue
        priority = 0 if is_priority_section(heading) else 1
        selected.append((priority, i, s))

    # Priority sections first, then others
    selected.sort(key=lambda x: (x[0], x[1]))

    parts: list[str] = []
    total = 0
    for _, _, s in selected:
        heading = s["heading"]
        text    = s["text"][:2500]          # cap individual section length
        chunk   = f"### {heading}\n{text}"
        if total + len(chunk) > max_chars:
            break
        parts.append(chunk)
        total += len(chunk)

    return "\n\n".join(parts)


def call_with_retry(client: OpenAI, **kwargs) -> object:
    """
    Call client.responses.create(**kwargs) with exponential backoff on 429.
    Respects the retry-after-ms header when the API provides it.
    Delays: ~10s, ~20s, ~40s before giving up.
    """
    base_delays = [10, 20, 40]
    for attempt, base_delay in enumerate(base_delays + [None]):
        try:
            return client.responses.create(**kwargs)
        except RateLimitError as e:
            if base_delay is None:
                # exhausted all retries — re-raise for the caller to handle
                raise

            delay = float(base_delay)

            # Prefer the server-supplied wait time when available
            resp_headers = getattr(getattr(e, "response", None), "headers", {})
            if resp_headers:
                print(f"  Rate-limit response headers:")
                for h in ("retry-after-ms", "retry-after",
                          "x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens",
                          "x-ratelimit-reset-tokens"):
                    val = resp_headers.get(h)
                    if val:
                        print(f"    {h}: {val}")
                retry_after_ms = resp_headers.get("retry-after-ms")
                retry_after_s  = resp_headers.get("retry-after")
                if retry_after_ms:
                    delay = max(delay, int(retry_after_ms) / 1000 + 1)
                elif retry_after_s:
                    delay = max(delay, float(retry_after_s) + 1)

            print(f"  ⚠  429 rate limit (attempt {attempt + 1}/3). "
                  f"Waiting {delay:.0f}s before retry...")
            time.sleep(delay)


def build_prompt(proposed_extract: str, final_extract: str,
                 proposed_meta: dict, final_meta: dict) -> str:
    return f"""You are an expert policy analyst. You have been given extracts from two official \
Federal Register documents — the proposed rule and the final rule for the FTC Non-Compete Clause Rule. \
Your task is to produce a structured, evidence-grounded analysis.

CRITICAL INSTRUCTIONS:
- Base every claim on the source text provided. Do not invent evidence.
- When quoting or paraphrasing, attribute to the correct document and section.
- Clearly separate official rule language, factual findings, and AI interpretation.
- Do not recommend whether the policy is good or bad.
- Preserve uncertainty. If evidence is insufficient, say so.
- Use "source_type": "official" only for text directly from rule language.
- Use "source_type": "ai" for your synthesis and interpretation.
- Be precise about numbers, dates, thresholds, and definitions found in the text.

DOCUMENT 1 — PROPOSED RULE
Title: {proposed_meta['title']}
Published: {proposed_meta['publication_date']}
Type: {proposed_meta['document_type']}
Source: {proposed_meta['source_url']}

{proposed_extract}

---

DOCUMENT 2 — FINAL RULE
Title: {final_meta['title']}
Published: {final_meta['publication_date']}
Type: {final_meta['document_type']}
Source: {final_meta['source_url']}

{final_extract}

---

Return ONLY valid JSON matching this exact schema. No markdown fences, no extra text.

{{
  "policy_summary": "<2-3 paragraph plain-language summary of what the rule does>",
  "key_changes": [
    "<specific change 1 — cite section if visible>",
    "<specific change 2>",
    "..."
  ],
  "affected_stakeholders": [
    {{
      "group": "<group name>",
      "description": "<how they are affected>",
      "impact": "<positive | negative | mixed | neutral>",
      "evidence_excerpt": "<direct quote or close paraphrase from the source text>",
      "source_document": "<Proposed Rule | Final Rule>",
      "source_section": "<heading or section identifier from the extract>"
    }}
  ],
  "important_definitions": [
    {{
      "term": "<defined term>",
      "definition": "<definition as stated in the rule>",
      "source_document": "<Proposed Rule | Final Rule>",
      "source_section": "<section heading>"
    }}
  ],
  "findings": [
    {{
      "claim": "<a specific, verifiable claim about the policy>",
      "source_type": "<official | ai>",
      "confidence": "<high | medium | low>",
      "evidence": [
        {{
          "excerpt": "<exact quote or close paraphrase>",
          "source_document": "<Proposed Rule | Final Rule>",
          "source_section": "<section heading>"
        }}
      ]
    }}
  ],
  "uncertainty_or_limitations": [
    "<something this analysis cannot determine from the provided text>",
    "..."
  ]
}}"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Policy Analysis Pipeline")
    print("FTC Non-Compete Clause Rule → Azure OpenAI → structured JSON")
    print()

    # 1. Validate credentials
    endpoint, api_key, deployment = check_env()
    print(f"✓ Foundry endpoint: {endpoint}")
    print(f"  Deployment: {deployment}")

    # 2. Load documents
    print("\n→ Loading Federal Register documents...")
    proposed = load_rule("federal_register_proposed_rule.json")
    final    = load_rule("federal_register_final_rule.json")
    print(f"  Proposed Rule: {len(proposed['sections'])} sections, "
          f"{len(proposed['full_text']):,} chars")
    print(f"  Final Rule:    {len(final['sections'])} sections, "
          f"{len(final['full_text']):,} chars")

    # 3. Extract key sections
    print(f"\n→ Extracting priority sections (max {MAX_CHARS_PER_DOC:,} chars each)...")
    proposed_extract = extract_key_sections(proposed, MAX_CHARS_PER_DOC)
    final_extract    = extract_key_sections(final, MAX_CHARS_PER_DOC)
    print(f"  Proposed extract: {len(proposed_extract):,} chars")
    print(f"  Final extract:    {len(final_extract):,} chars")

    # 4. Build prompt
    prompt = build_prompt(
        proposed_extract, final_extract,
        {k: proposed[k] for k in ("title", "publication_date", "document_type", "source_url")},
        {k: final[k]    for k in ("title", "publication_date", "document_type", "source_url")},
    )
    prompt_tokens_est = len(prompt) // 4
    print(f"\n→ Prompt size: ~{prompt_tokens_est:,} tokens (estimated)")

    # 5. Call Azure AI Foundry via OpenAI-compatible Responses API
    print(f"\n→ Sending to Foundry ({deployment}) via /openai/v1/responses ...")
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
                "You produce accurate, evidence-grounded analysis of regulatory documents. "
                "You always cite your sources and clearly label AI interpretation vs. official language. "
                "You output only valid JSON as instructed."
            ),
            input=prompt,
            text={"format": {"type": "json_object"}},
            temperature=0.1,    # low temperature for factual accuracy
            max_output_tokens=2500,
        )
    except RateLimitError as e:
        print(f"\n❌  Rate limit persisted after 3 retries: {e}")
        resp_headers = getattr(getattr(e, "response", None), "headers", {})
        if resp_headers:
            print("  Final rate-limit headers:")
            for h in ("retry-after-ms", "retry-after",
                      "x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens"):
                val = resp_headers.get(h)
                if val:
                    print(f"    {h}: {val}")
        print("\n  Suggestion: wait 60s and retry, or check your TPM quota in Azure portal.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌  Foundry API call failed: {e}")
        print()
        error_msg = str(e).lower()
        if "401" in error_msg or "authentication" in error_msg or "unauthorized" in error_msg:
            print("   → API key is invalid or expired. Check AZURE_OPENAI_API_KEY.")
        elif "404" in error_msg or "not found" in error_msg:
            print("   → Endpoint or deployment not found.")
            print("     Check AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT_NAME.")
        elif "400" in error_msg:
            print("   → Bad request. Check that the deployment name matches exactly.")
        sys.exit(1)

    raw_json = response.output_text
    usage    = response.usage
    print(f"  ✓ Response received")
    print(f"    Input tokens:  {usage.input_tokens:,}")
    print(f"    Output tokens: {usage.output_tokens:,}")
    print(f"    Total tokens:  {usage.total_tokens:,}")

    # 6. Parse and validate
    print("\n→ Parsing response JSON...")
    try:
        analysis = json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f"❌  Model returned invalid JSON: {e}")
        print("   Raw response preview:")
        print(raw_json[:500])
        sys.exit(1)

    required_keys = {
        "policy_summary", "key_changes", "affected_stakeholders",
        "important_definitions", "findings", "uncertainty_or_limitations",
    }
    missing_keys = required_keys - set(analysis.keys())
    if missing_keys:
        print(f"⚠  Response missing expected keys: {missing_keys}")
        print("   Saving anyway — review output file manually.")

    # 7. Enrich with metadata and source info
    analysis["_metadata"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deployment": deployment,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "source_documents": [
            {
                "label": "Proposed Rule",
                "document_number": proposed["document_number"],
                "title": proposed["title"],
                "publication_date": proposed["publication_date"],
                "source_url": proposed["source_url"],
            },
            {
                "label": "Final Rule",
                "document_number": final["document_number"],
                "title": final["title"],
                "publication_date": final["publication_date"],
                "source_url": final["source_url"],
            },
        ],
    }

    # 8. Save
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"\n✓ Saved {OUTPUT_FILE.name} ({size_kb:.1f} KB)")

    # 9. Quick preview
    print("\n─── Output preview ───────────────────────────────────────")
    print(f"  policy_summary:          {len(analysis.get('policy_summary',''))} chars")
    print(f"  key_changes:             {len(analysis.get('key_changes', []))} items")
    print(f"  affected_stakeholders:   {len(analysis.get('affected_stakeholders', []))} groups")
    print(f"  important_definitions:   {len(analysis.get('important_definitions', []))} terms")
    print(f"  findings:                {len(analysis.get('findings', []))} findings")
    print(f"  uncertainty_items:       {len(analysis.get('uncertainty_or_limitations', []))} items")
    print()
    if "findings" in analysis and analysis["findings"]:
        print("  First finding:")
        f0 = analysis["findings"][0]
        print(f"    Claim:      {f0.get('claim','')[:120]}...")
        print(f"    Type:       {f0.get('source_type')}")
        print(f"    Confidence: {f0.get('confidence')}")
    print("──────────────────────────────────────────────────────────")
    print("\n✓ Analysis complete.")


if __name__ == "__main__":
    main()
