"""
analyze_news.py

Loads data/raw/news_articles.json, sends article metadata to GPT-4o via
Azure AI Foundry, and saves structured analysis to
data/processed/news_analysis.json.

Usage:
    cd backend && source venv/bin/activate
    python scripts/analyze_news.py

Requires:
    - data/raw/news_articles.json  (run fetch_news.py first)
    - AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME in .env
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

INPUT_FILE  = _root / "data" / "raw"       / "news_articles.json"
OUTPUT_FILE = _root / "data" / "processed" / "news_analysis.json"

MAX_OUTPUT_TOKENS = 4000


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


def format_article(a: dict, index: int) -> str:
    return (
        f"[Article {index+1}]\n"
        f"Headline: {a['headline']}\n"
        f"Publication: {a.get('publication','Unknown')}\n"
        f"Date: {a.get('date','')[:10]}\n"
        f"Description: {a.get('description','')[:300]}\n"
        f"URL: {a.get('url','')}"
    )


def build_prompt(articles: list[dict], meta: dict) -> str:
    formatted = "\n\n".join(format_article(a, i) for i, a in enumerate(articles))
    return f"""You are a professional government policy analyst reviewing news coverage
of the FTC Non-Compete Clause Rule.

CRITICAL INSTRUCTIONS:
- Do NOT say whether the rule is good or bad.
- Do NOT make policy recommendations.
- Remain neutral; report what sources say, not what you think.
- Distinguish factual news reporting from analysis or opinion where possible.
- Base every claim only on the article metadata provided.
- Do not invent or assume article content beyond the headline and description.
- Use "source_type": "reporting" for straight news; "analysis" for analytical
  pieces; "opinion" for clearly labeled op-eds/editorials.
- Every key development must reference a specific article by its number.

SOURCE NOTE: {meta.get('source_note','')}
ARTICLES ANALYZED: {len(articles)}

{formatted}

Return ONLY valid JSON matching this exact schema. No markdown fences.

{{
  "summary": "<2–3 sentence neutral overview of what news coverage focused on>",
  "articles": [
    {{
      "headline": "<exact headline from the article>",
      "publication": "<publication name>",
      "date": "<date string>",
      "url": "<url>",
      "source_type": "<reporting | analysis | opinion>",
      "summary": "<1–2 sentence neutral summary of what this article covers>",
      "policy_issue": "<specific policy issue this article addresses>"
    }}
  ],
  "key_developments": [
    "<important development reported, with article number reference e.g. [Article 3]>"
  ],
  "coverage_themes": [
    "<theme across multiple articles>"
  ],
  "limitations": [
    "<honest limitation, e.g. small sample, recency, source diversity>"
  ]
}}"""


def main() -> None:
    print("News Analysis Pipeline")
    print("news_articles.json → Azure AI Foundry → news_analysis.json")
    print()

    endpoint, api_key, deployment = check_env()
    print(f"✓ Foundry endpoint: {endpoint}")
    print(f"  Deployment: {deployment}")

    if not INPUT_FILE.exists():
        print(f"\n❌  {INPUT_FILE.name} not found. Run fetch_news.py first.")
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    articles = raw.get("articles", [])
    if not articles:
        print("❌  No articles in input file.")
        sys.exit(1)

    print(f"\n→ Loaded {len(articles)} articles from {INPUT_FILE.name}")

    prompt = build_prompt(articles, raw)
    print(f"→ Prompt size: ~{len(prompt)//4:,} tokens (estimated)")

    client = OpenAI(base_url=f"{endpoint}/openai/v1/", api_key=api_key)
    print(f"\n→ Sending to Foundry ({deployment})…")

    try:
        response = call_with_retry(
            client,
            model=deployment,
            instructions=(
                "You are a professional government policy analyst. "
                "You summarise news coverage neutrally, distinguishing factual "
                "reporting from opinion. You output only valid JSON."
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
        analysis = json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f"❌  Invalid JSON from model: {e}\n{raw_json[:300]}")
        sys.exit(1)

    # Back-fill URLs from raw data where model may have shortened them
    raw_url_map = {a["headline"].strip(): a["url"] for a in articles}
    for art in analysis.get("articles", []):
        if not art.get("url"):
            art["url"] = raw_url_map.get(art.get("headline", "").strip(), "")

    analysis["_metadata"] = {
        "generated_at":      datetime.now(timezone.utc).isoformat(),
        "deployment":        deployment,
        "articles_analyzed": len(articles),
        "input_tokens":      usage.input_tokens,
        "output_tokens":     usage.output_tokens,
        "source_note":       raw.get("source_note", ""),
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"\n✓ Saved {OUTPUT_FILE.name} ({kb:.1f} KB)")
    print(f"\n─── Preview ───────────────────────────────────────────")
    print(f"  summary:           {len(analysis.get('summary',''))} chars")
    print(f"  articles:          {len(analysis.get('articles',[]))}")
    print(f"  key_developments:  {len(analysis.get('key_developments',[]))}")
    print(f"  coverage_themes:   {len(analysis.get('coverage_themes',[]))}")
    print(f"  limitations:       {len(analysis.get('limitations',[]))}")
    print(f"────────────────────────────────────────────────────────")
    print("\n✓ Analysis complete.")


if __name__ == "__main__":
    main()
