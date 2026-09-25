"""
Fetch and parse FTC Non-Compete Clause Rule documents from the Federal Register API.

Saves two JSON files to data/raw/:
  - federal_register_proposed_rule.json  (document 2023-00414, published 2023-01-19)
  - federal_register_final_rule.json     (document 2024-09171, published 2024-05-07)

Usage:
  python scripts/fetch_federal_register.py

No API key required. Federal Register API is free and public.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

FR_API_BASE = "https://www.federalregister.gov/api/v1"

DOCUMENTS = [
    {
        "document_number": "2023-00414",
        "label": "proposed_rule",
        "output_file": "federal_register_proposed_rule.json",
    },
    {
        "document_number": "2024-09171",
        "label": "final_rule",
        "output_file": "federal_register_final_rule.json",
    },
]

METADATA_FIELDS = [
    "title", "publication_date", "document_number", "type", "abstract",
    "html_url", "full_text_xml_url", "body_html_url", "page_length",
    "agencies", "docket_ids", "cfr_references",
]

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"


def fetch_metadata(client: httpx.Client, document_number: str) -> dict:
    fields_qs = "&".join(f"fields[]={f}" for f in METADATA_FIELDS)
    url = f"{FR_API_BASE}/articles/{document_number}.json?{fields_qs}"
    response = client.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_body_html(client: httpx.Client, body_html_url: str) -> str:
    response = client.get(body_html_url, timeout=60)
    response.raise_for_status()
    return response.text


def extract_sections(html: str) -> list[dict]:
    """Parse FR body HTML into sections. Headings h1-h4 delimit sections."""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup.select(".document-headings, .fr-seal-block, .end-matter"):
        tag.decompose()

    sections: list[dict] = []
    current_heading = "Preamble"
    current_paragraphs: list[str] = []

    for element in soup.find_all(["h1", "h2", "h3", "h4", "p"]):
        text = element.get_text(separator=" ", strip=True)
        if not text:
            continue

        if element.name in ("h1", "h2", "h3", "h4"):
            if current_paragraphs:
                sections.append({
                    "heading": current_heading,
                    "text": " ".join(current_paragraphs),
                })
            current_heading = text
            current_paragraphs = []
        elif len(text) > 20:
            current_paragraphs.append(text)

    if current_paragraphs:
        sections.append({"heading": current_heading, "text": " ".join(current_paragraphs)})

    return sections


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_full_text(sections: list[dict]) -> str:
    return "\n\n".join(f"## {s['heading']}\n\n{s['text']}" for s in sections)


def process_document(doc_config: dict) -> None:
    document_number = doc_config["document_number"]
    output_path = DATA_DIR / doc_config["output_file"]

    print(f"\n{'='*60}")
    print(f"Fetching {document_number} ({doc_config['label']})...")

    with httpx.Client(follow_redirects=True) as client:
        print("  → Fetching metadata...")
        metadata = fetch_metadata(client, document_number)

        body_html_url = metadata.get("body_html_url")
        if not body_html_url:
            print(f"  ✗ No body_html_url for {document_number}")
            sys.exit(1)

        print(f"  → Fetching body HTML...")
        html = fetch_body_html(client, body_html_url)
        print(f"     Size: {len(html):,} chars")

    print("  → Parsing sections...")
    sections = extract_sections(html)
    print(f"     Extracted {len(sections)} sections")

    # Cap section text to keep JSON files manageable
    for s in sections:
        s["text"] = clean_text(s["text"])[:4000]

    agencies = [
        a.get("raw_name", a.get("name", ""))
        for a in metadata.get("agencies", [])
    ]

    output = {
        "document_number": metadata["document_number"],
        "title": metadata["title"],
        "publication_date": metadata["publication_date"],
        "document_type": metadata["type"],
        "abstract": metadata.get("abstract", ""),
        "agencies": agencies,
        "docket_ids": metadata.get("docket_ids", []),
        "cfr_references": metadata.get("cfr_references", []),
        "source_url": metadata["html_url"],
        "body_html_url": body_html_url,
        "page_length": metadata.get("page_length"),
        "sections": sections,
        "full_text": build_full_text(sections),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    size_kb = output_path.stat().st_size / 1024
    print(f"  ✓ Saved {output_path.name} ({size_kb:.1f} KB, {len(sections)} sections)")


def main():
    print("Federal Register Data Collection")
    print("Policy: FTC Non-Compete Clause Rule")
    print(f"Output: {DATA_DIR}")

    for doc in DOCUMENTS:
        process_document(doc)

    print(f"\n✓ Complete. Files saved to {DATA_DIR}")


if __name__ == "__main__":
    main()
