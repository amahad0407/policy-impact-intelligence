from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI(
    title="Policy Impact Intelligence API",
    version="0.2.0",
)

_allowed_origins = ["http://localhost:3000"]
_frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip().rstrip("/")
if _frontend_origin:
    _allowed_origins.append(_frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ROOT = Path(__file__).resolve().parent.parent.parent
_PROCESSED = _ROOT / "data" / "processed"
_RAW       = _ROOT / "data" / "raw"
_STATUS    = _PROCESSED / "data_status.json"
_BACKEND   = Path(__file__).resolve().parent.parent   # backend/
_PYTHON    = sys.executable


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_status() -> dict:
    return _load_json(_STATUS) or {
        "last_checked": None,
        "sources": {
            "federal_register": {"last_checked": None, "note": "Archived documents — publication dates fixed"},
            "news": {"last_checked": None, "latest_article_date": None, "article_count": 0},
            "comments": {"last_checked": None, "note": "Comment period closed April 2023"},
        },
    }


def _write_status(s: dict) -> None:
    _save_json(_STATUS, s)


# ---------------------------------------------------------------------------
# Static data endpoints (unchanged)
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/overview")
def overview():
    path = _PROCESSED / "policy_summary.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run: python scripts/analyze_policy.py")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/feedback")
def feedback():
    path = _PROCESSED / "comments_analysis.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run: python scripts/analyze_comments.py")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/news")
def news():
    path = _PROCESSED / "news_analysis.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run: python scripts/analyze_news.py")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/briefing")
def briefing():
    path = _PROCESSED / "briefing_analysis.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run: python scripts/analyze_briefing.py")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/comparison")
def comparison():
    path = _PROCESSED / "comparison_analysis.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run: python scripts/analyze_comparison.py")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Data freshness / status
# ---------------------------------------------------------------------------

@app.get("/api/status")
def data_status():
    """Freshness metadata across processed files. Powers the 'Last Updated' indicator."""
    analysis: dict[str, dict | None] = {}
    for name, filename in [
        ("policy_summary",     "policy_summary.json"),
        ("news_analysis",      "news_analysis.json"),
        ("comments_analysis",  "comments_analysis.json"),
        ("comparison_analysis","comparison_analysis.json"),
        ("briefing_analysis",  "briefing_analysis.json"),
    ]:
        data = _load_json(_PROCESSED / filename)
        analysis[name] = (
            {"generated_at": data.get("_metadata", {}).get("generated_at"),
             "deployment":   data.get("_metadata", {}).get("deployment")}
            if data else None
        )

    generated_times = sorted(
        v["generated_at"] for v in analysis.values()
        if v and v.get("generated_at")
    )
    raw_news = _load_json(_RAW / "news_articles.json") or {}
    raw_articles = raw_news.get("articles", [])
    dates = sorted(a.get("date", "") for a in raw_articles if a.get("date"))
    status = _read_status()

    return {
        "analysis": analysis,
        "analysis_last_generated": generated_times[-1] if generated_times else None,
        "last_checked": status.get("last_checked"),
        "sources": {
            "federal_register": {
                "last_checked": status["sources"].get("federal_register", {}).get("last_checked"),
                "kind": "archived",
                "note": "Archived historical documents — publication dates fixed",
            },
            "news": {
                "last_checked":        status["sources"].get("news", {}).get("last_checked"),
                "kind":                "refreshable",
                "latest_article_date": dates[-1] if dates else None,
                "article_count":       len(raw_articles),
            },
            "comments": {
                "last_checked": status["sources"].get("comments", {}).get("last_checked"),
                "kind": "closed",
                "note": "Comment period closed April 2023",
            },
        },
    }


# ---------------------------------------------------------------------------
# Policy registry (single real policy today; ready for more)
# ---------------------------------------------------------------------------

def _policies_list() -> list[dict]:
    """Build the list of real, analyzed policies from processed data. Only one today."""
    out: list[dict] = []
    policy_data = _load_json(_PROCESSED / "policy_summary.json")
    if policy_data:
        meta = policy_data.get("_metadata", {})
        out.append({
            "id":            "ftc-non-compete-2024",
            "title":         "FTC Non-Compete Clause Rule",
            "short_title":   "FTC Non-Compete Rule",
            "agency":        "Federal Trade Commission",
            "docket_id":     "FTC-2023-0007",
            "cfr_part":      "16 CFR Part 910",
            "status":        "Set aside (vacated)",
            "status_detail": "Vacated by federal court Aug 20, 2024; removed from CFR Feb 2026.",
            "jurisdiction":  "United States",
            "generated_at":  meta.get("generated_at"),
            "is_active":     True,
        })
    return out


def _resolve_policy(policy_id: str | None) -> dict | None:
    """Return the requested policy, or the active/first one when id is missing/unknown."""
    available = _policies_list()
    if not available:
        return None
    if policy_id:
        match = next((p for p in available if p["id"] == policy_id), None)
        if match:
            return match
    return next((p for p in available if p.get("is_active")), available[0])


@app.get("/api/policies")
def policies():
    """List policies available in the system. Only real, analyzed policies appear."""
    out = _policies_list()
    return {"policies": out, "count": len(out)}


# ---------------------------------------------------------------------------
# Refresh workflow
# ---------------------------------------------------------------------------

GNEWS_QUERIES = [
    "FTC non-compete rule ban 2024",
    "non-compete clause federal rule court",
    "FTC Ryan LLC non-compete ruling",
]
GNEWS_BASE = "https://news.google.com/rss/search"


def _parse_rss_articles(xml_text: str) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    articles = []
    for item in root.findall(".//item"):
        title  = (item.findtext("title") or "").strip()
        link   = (item.findtext("link") or "").strip()
        pub    = item.findtext("pubDate") or ""
        desc   = (item.findtext("description") or "").strip()
        source = item.findtext("source") or ""
        date_iso = pub
        try:
            from email.utils import parsedate_to_datetime
            date_iso = parsedate_to_datetime(pub).isoformat()
        except Exception:
            pass
        clean_desc = re.sub(r"<[^>]+>", "", desc).strip()
        if title and link:
            articles.append({
                "headline": title, "publication": source or "Unknown",
                "source_url": link, "url": link, "date": date_iso,
                "description": clean_desc[:300],
            })
    return articles


def _check_and_update_news() -> tuple[bool, int]:
    """
    Fetch Google News RSS, add only articles newer than the most recent stored one.
    Never re-downloads existing articles. Returns (changed, new_count).
    """
    news_path = _RAW / "news_articles.json"
    existing_data = _load_json(news_path) or {"articles": [], "fetched_at": None}
    existing_articles = existing_data.get("articles", [])
    existing_dates = sorted(a.get("date", "") for a in existing_articles if a.get("date"))
    latest_existing = existing_dates[-1] if existing_dates else ""
    existing_urls = {a.get("url", "") for a in existing_articles} | \
                    {a.get("source_url", "") for a in existing_articles}

    new_articles: list[dict] = []
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for query in GNEWS_QUERIES:
            params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
            url = f"{GNEWS_BASE}?{urllib.parse.urlencode(params)}"
            try:
                resp = client.get(url)
                resp.raise_for_status()
                fetched = _parse_rss_articles(resp.text)
            except Exception:
                continue
            for a in fetched:
                url_key = a.get("url", "") or a.get("source_url", "")
                if url_key in existing_urls:
                    continue
                if not latest_existing or a.get("date", "") > latest_existing:
                    new_articles.append(a)
                    existing_urls.add(url_key)

    if not new_articles:
        return False, 0

    all_articles = new_articles + existing_articles
    all_articles.sort(key=lambda x: x.get("date", ""), reverse=True)
    existing_data["articles"] = all_articles
    existing_data["article_count"] = len(all_articles)
    existing_data["fetched_at"] = _now()
    existing_data.setdefault("query_terms", GNEWS_QUERIES)
    _save_json(news_path, existing_data)
    return True, len(new_articles)


def _run_script(script_name: str, timeout: int = 180) -> tuple[bool, str]:
    """Run a backend analysis script via subprocess. Returns (success, message)."""
    script_path = _BACKEND / "scripts" / script_name
    if not script_path.exists():
        return False, f"Script not found: {script_name}"
    try:
        result = subprocess.run(
            [_PYTHON, str(script_path)],
            cwd=str(_BACKEND), capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "PYTHONPATH": str(_BACKEND)},
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()[:300]
            return False, f"exit {result.returncode}: {err}"
        return True, "ok"
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    except Exception as e:
        return False, str(e)


@app.post("/api/refresh")
def refresh_data(force: bool = False):
    """
    Check live sources and refresh only what changed.
      1. Google News RSS  → refreshable (fetch newer articles)
      2. Federal Register → archived (no refresh)
      3. Regulations.gov  → closed comment period (no refresh)
    Azure OpenAI is only re-invoked when source data changed (or force=True),
    keeping token usage conservative.
    """
    started_at = _now()
    result: dict = {
        "started_at": started_at, "sources_checked": [], "sources_updated": [],
        "analysis_rerun": [], "errors": [], "changed": False, "new_articles": 0,
        "completed_at": None, "note": "",
    }
    status = _read_status()
    status["last_checked"] = started_at

    # 1. News (refreshable)
    result["sources_checked"].append("google_news_rss")
    try:
        news_changed, new_count = _check_and_update_news()
        status["sources"]["news"]["last_checked"] = started_at
        if news_changed:
            result["sources_updated"].append("news")
            result["changed"] = True
            result["new_articles"] = new_count
        raw_news = _load_json(_RAW / "news_articles.json") or {}
        d = sorted(a.get("date", "") for a in raw_news.get("articles", []) if a.get("date"))
        status["sources"]["news"]["latest_article_date"] = d[-1] if d else None
        status["sources"]["news"]["article_count"] = raw_news.get("article_count", 0)
    except Exception as e:
        result["errors"].append(f"news_check: {str(e)}")

    # 2. Federal Register (archived) & 3. Regulations.gov (closed)
    result["sources_checked"].extend(["federal_register", "regulations_gov"])
    status["sources"]["federal_register"]["last_checked"] = started_at
    status["sources"]["comments"]["last_checked"] = started_at

    # 4. Re-run AI analysis only when needed
    if result["changed"] or force:
        if "news" in result["sources_updated"] or force:
            ok, msg = _run_script("analyze_news.py")
            result["analysis_rerun"].append("news_analysis") if ok else result["errors"].append(f"analyze_news: {msg}")
        ok, msg = _run_script("analyze_briefing.py")
        result["analysis_rerun"].append("briefing_analysis") if ok else result["errors"].append(f"analyze_briefing: {msg}")
    else:
        result["note"] = "No new source data found — AI analysis not re-run."

    result["completed_at"] = _now()
    _write_status(status)
    return result


# ---------------------------------------------------------------------------
# Hypothetical policy analysis
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    title: str
    description: str
    jurisdiction: str
    policy_type: str


_SYSTEM_INSTRUCTIONS = """You are a professional government policy analyst specializing in regulatory impact assessment.

CRITICAL RULES — follow exactly:
1. This is HYPOTHETICAL analysis based ONLY on the policy description provided by the user.
2. Do NOT invent real public comments, news coverage, polling, stakeholder statements, statistics, or citations to real sources.
3. Do NOT present simulated reactions as actual public sentiment. Never say "residents oppose this" — say "residents may raise concerns about...".
4. If the description lacks enough detail to make a claim, explicitly state that additional evidence or information would be required.
5. Use conditional language throughout: "may", "could", "analysts should investigate", "it is plausible that".
6. Output ONLY valid JSON matching the schema. No prose outside the JSON.

Output schema (all fields required):
{
  "summary": "2-3 sentence plain-language summary of the policy as described.",
  "key_changes": ["concise statement of a change, requirement, or provision", ...],
  "affected_stakeholders": [
    {"group": "group name", "description": "how they may be affected — conditional language required", "impact_direction": "positive|negative|mixed|unclear"},
    ...
  ],
  "potential_benefits": ["benefit as described or reasonably inferred — no invented evidence", ...],
  "potential_concerns": ["concern framed conditionally — no fabricated opposition data", ...],
  "implementation_questions": ["open question an analyst should investigate before drawing conclusions", ...],
  "areas_of_disagreement": ["topic where different interests may predictably conflict", ...],
  "uncertainties": ["aspect of the policy description that is unclear, unspecified, or requires additional information", ...],
  "disclaimer": "Single sentence stating this is AI-generated hypothetical analysis based solely on the provided description, not real-world evidence."
}"""


def _build_prompt(req: AnalyzeRequest) -> str:
    return (
        f"Policy Title: {req.title}\n"
        f"Jurisdiction: {req.jurisdiction}\n"
        f"Policy Type: {req.policy_type}\n\n"
        f"Policy Description:\n{req.description}\n\n"
        "Analyze this hypothetical policy following your instructions. "
        "Return only the JSON object — no markdown, no prose."
    )


@app.post("/api/analyze-policy")
def analyze_policy(req: AnalyzeRequest):
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
    api_key  = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
    deploy   = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o").strip()

    if not endpoint or not api_key:
        raise HTTPException(
            status_code=503,
            detail="Azure OpenAI credentials not configured. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in backend/.env",
        )

    client = OpenAI(
        base_url=f"{endpoint}/openai/v1/",
        api_key=api_key,
    )

    try:
        response = client.responses.create(
            model=deploy,
            instructions=_SYSTEM_INSTRUCTIONS,
            input=_build_prompt(req),
            text={"format": {"type": "json_object"}},
            temperature=0.2,
            max_output_tokens=2000,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Azure OpenAI error: {str(e)}")

    raw = response.output_text
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Model returned invalid JSON. Try again.")

    result["_meta"] = {
        "title": req.title,
        "jurisdiction": req.jurisdiction,
        "policy_type": req.policy_type,
        "description": req.description,
        "deployment": deploy,
        "hypothetical": True,
    }
    return result


# ---------------------------------------------------------------------------
# Evidence search — deterministic keyword search over processed data.
# Searches local analysis files ONLY. Never the internet, never GPT.
# Provenance follows the app's system: official / opinion / reporting / ai.
# ---------------------------------------------------------------------------

_PROV_LABELS = {
    "official":  "Official Policy Language",
    "opinion":   "Public Opinion",
    "reporting": "Factual Reporting",
    "ai":        "AI Interpretation",
}

_POLICY_NAME = "FTC Non-Compete Clause Rule"


def _clip(text: str, limit: int = 320) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _rec(category: str, provenance: str, title: str, excerpt: str,
         *, date: str | None = None, source: str | None = None,
         url: str | None = None) -> dict:
    return {
        "category": category,
        "provenance": provenance,
        "provenance_label": _PROV_LABELS.get(provenance, "AI Interpretation"),
        "title": _clip(title, 160),
        "excerpt": _clip(excerpt, 320),
        "date": date or None,
        "source": source or None,
        "policy": _POLICY_NAME,
        "url": url or None,
    }


def _build_search_index() -> list[dict]:
    """Flatten every piece of processed evidence into searchable records."""
    records: list[dict] = []

    # --- Official policy language (policy_summary.json) ---
    ps = _load_json(_PROCESSED / "policy_summary.json") or {}
    for ch in ps.get("key_changes", []):
        records.append(_rec("Key Policy Change", "official", "Key policy change",
                            ch, source="FTC Non-Compete Rule — Final Rule"))
    for d in ps.get("important_definitions", []):
        src = " — ".join(x for x in [d.get("source_document"), d.get("source_section")] if x)
        records.append(_rec("Definition", "official", d.get("term", "Definition"),
                            d.get("definition", ""), source=src or "Final Rule"))
    for s in ps.get("affected_stakeholders", []):
        records.append(_rec("Stakeholder", "official", s.get("group", "Stakeholder"),
                            s.get("evidence_excerpt") or s.get("description", ""),
                            source=s.get("source_document") or "Final Rule"))
    for f in ps.get("findings", []):
        st = f.get("source_type", "ai")
        st = st if st in _PROV_LABELS else "ai"
        records.append(_rec("Policy Finding", st, "Finding", f.get("claim", ""),
                            source="Policy analysis"))

    # --- Public opinion (comments_analysis.json) ---
    ca = _load_json(_PROCESSED / "comments_analysis.json") or {}
    for t in ca.get("themes", []):
        n = t.get("comment_count")
        src = f"Regulations.gov · {n} comments" if n else "Regulations.gov"
        records.append(_rec("Public Comment Theme", "opinion", t.get("theme", "Theme"),
                            t.get("description", ""), source=src))
        for e in t.get("evidence", []):
            records.append(_rec("Public Comment", "opinion", "Public comment",
                                e.get("excerpt", ""),
                                source=e.get("comment_id") or "Regulations.gov",
                                url=e.get("source_url")))
    for v in ca.get("viewpoints", []):
        n = v.get("comment_count")
        src = f"Regulations.gov · {n} comments" if n else "Regulations.gov"
        records.append(_rec("Public Viewpoint", "opinion", v.get("label", "Viewpoint"),
                            v.get("description", ""), source=src))
        for e in v.get("evidence", []):
            records.append(_rec("Public Comment", "opinion", "Public comment",
                                e.get("excerpt", ""),
                                source=e.get("comment_id") or "Regulations.gov",
                                url=e.get("source_url")))

    # --- Factual reporting (news_analysis.json) ---
    na = _load_json(_PROCESSED / "news_analysis.json") or {}
    for a in na.get("articles", []):
        records.append(_rec("News Article", "reporting", a.get("headline", "Article"),
                            a.get("summary") or a.get("policy_issue", ""),
                            date=a.get("date"), source=a.get("publication"),
                            url=a.get("url")))
    for dv in na.get("key_developments", []):
        records.append(_rec("News Development", "reporting", "News development",
                            dv, source="News coverage"))

    # --- Proposed vs final comparison — analytical synthesis (not official text) ---
    cmp = _load_json(_PROCESSED / "comparison_analysis.json") or {}
    for k in cmp.get("key_changes", []):
        records.append(_rec("Policy Comparison", "ai", k.get("topic", "Comparison"),
                            k.get("change_description", ""),
                            source="Proposed → Final Rule"))

    # --- Analyst briefing synthesis (briefing_analysis.json) ---
    br = _load_json(_PROCESSED / "briefing_analysis.json") or {}
    gen = br.get("_metadata", {}).get("generated_at")
    if br.get("executive_summary"):
        records.append(_rec("Briefing", "ai", "Executive summary",
                            br["executive_summary"], date=gen, source="Analyst Briefing"))
    if br.get("policy_context"):
        records.append(_rec("Briefing", "ai", "Policy context",
                            br["policy_context"], date=gen, source="Analyst Briefing"))
    for a in br.get("areas_of_alignment", []):
        records.append(_rec("Area of Alignment", "ai", "Area of alignment",
                            a, date=gen, source="Analyst Briefing"))
    for a in br.get("areas_of_difference", []):
        records.append(_rec("Area of Difference", "ai", "Area of difference",
                            a, date=gen, source="Analyst Briefing"))
    for u in br.get("uncertainties_and_limitations", []):
        records.append(_rec("Uncertainty / Limitation", "ai", "Uncertainty / limitation",
                            u, date=gen, source="Analyst Briefing"))

    for i, r in enumerate(records):
        r["id"] = f"r{i}"
    return records


@app.get("/api/search")
def search_evidence(
    q: str = Query("", description="Keyword query"),
    limit: int = Query(40, ge=1, le=100),
):
    """
    Deterministic keyword search across the app's existing processed evidence.
    All query terms must appear in a record (AND). Title matches rank higher.
    No AI is used; the internet is never queried.
    """
    query = (q or "").strip()
    terms = [t for t in re.split(r"\s+", query.lower()) if t]
    if not terms:
        return {"query": query, "count": 0, "results": []}

    scored: list[tuple[int, int, dict]] = []
    for order, rec in enumerate(_build_search_index()):
        title = rec["title"].lower()
        hay = f"{rec['title']} {rec['excerpt']} {rec['category']} {rec.get('source') or ''}".lower()
        if not all(t in hay for t in terms):
            continue
        score = 0
        for t in terms:
            score += hay.count(t)
            if t in title:
                score += 5
        scored.append((score, order, rec))

    scored.sort(key=lambda x: (-x[0], x[1]))
    results = [r for _, _, r in scored[:limit]]
    return {"query": query, "count": len(results), "results": results}


# ---------------------------------------------------------------------------
# Export — analyst briefing (PDF) and structured data (JSON) for a policy.
# Uses only pre-generated local analysis. No credentials are exposed.
# ---------------------------------------------------------------------------

def _export_bundle(policy_id: str | None) -> tuple[dict, dict, str | None]:
    pol = _resolve_policy(policy_id)
    briefing = _load_json(_PROCESSED / "briefing_analysis.json")
    if not pol or not briefing:
        raise HTTPException(
            status_code=404,
            detail="Briefing data unavailable. Run: python scripts/analyze_briefing.py",
        )
    generated = data_status().get("analysis_last_generated")
    return pol, briefing, generated


@app.get("/api/export/briefing.json")
def export_briefing_json(policy: Optional[str] = Query(None)):
    """Structured export of the selected policy's briefing (data + provenance)."""
    pol, briefing, generated = _export_bundle(policy)
    payload = {
        "export_type": "analyst_briefing",
        "product": "Policy Impact Intelligence",
        "exported_at": _now(),
        "analysis_last_generated": generated,
        "policy": pol,
        "provenance_legend": _PROV_LABELS,
        "briefing": briefing,
    }
    body = json.dumps(payload, indent=2, ensure_ascii=False)
    headers = {"Content-Disposition": f'attachment; filename="{pol["id"]}-briefing.json"'}
    return Response(content=body, media_type="application/json", headers=headers)


def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return d.strftime("%b %d, %Y · %H:%M UTC")
    except Exception:
        return iso


_IMPACT_COLORS = {
    "positive": "#2E7D5B", "negative": "#B4553F",
    "mixed": "#8B7045", "neutral": "#5B6472", "unclear": "#5B6472",
}
_SRC_PROV = {"official": "official", "public_comment": "opinion", "news": "reporting"}


def _build_briefing_pdf(pol: dict, br: dict, generated: str | None) -> bytes:
    """Render a professional analyst briefing PDF from processed data."""
    from io import BytesIO
    from xml.sax.saxutils import escape
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        ListFlowable, ListItem, HRFlowable,
    )

    INK    = HexColor("#1B2430")
    HEAD   = HexColor("#1A2A44")
    ACCENT = HexColor("#5B84B0")
    MUTED  = HexColor("#5B6472")
    RULE   = HexColor("#C9D2DE")
    BOXBG  = HexColor("#F2F5F9")

    base = getSampleStyleSheet()
    S = {
        "label":  ParagraphStyle("label", parent=base["Normal"], fontName="Helvetica-Bold",
                                  fontSize=8, textColor=ACCENT, leading=11, spaceAfter=2),
        "title":  ParagraphStyle("title", parent=base["Normal"], fontName="Helvetica-Bold",
                                  fontSize=20, textColor=HEAD, leading=23, spaceAfter=4),
        "meta":   ParagraphStyle("meta", parent=base["Normal"], fontName="Helvetica",
                                  fontSize=8.5, textColor=MUTED, leading=13),
        "h2":     ParagraphStyle("h2", parent=base["Normal"], fontName="Helvetica-Bold",
                                  fontSize=12, textColor=HEAD, leading=15,
                                  spaceBefore=15, spaceAfter=5),
        "body":   ParagraphStyle("body", parent=base["Normal"], fontName="Helvetica",
                                  fontSize=9.5, textColor=INK, leading=14, alignment=TA_JUSTIFY),
        "th":     ParagraphStyle("th", parent=base["Normal"], fontName="Helvetica-Bold",
                                  fontSize=8.5, textColor=white, leading=11),
        "cell":   ParagraphStyle("cell", parent=base["Normal"], fontName="Helvetica",
                                  fontSize=8.5, textColor=INK, leading=12),
        "discl":  ParagraphStyle("discl", parent=base["Normal"], fontName="Helvetica-Oblique",
                                  fontSize=8.5, textColor=MUTED, leading=12.5),
    }

    def body(text: str):
        return Paragraph(escape(text), S["body"])

    def h2(text: str):
        return Paragraph(escape(text), S["h2"])

    def bullets(items):
        rows = [ListItem(Paragraph(escape(str(it)), S["body"]), spaceBefore=2)
                for it in items if str(it).strip()]
        return ListFlowable(rows, bulletType="bullet", bulletColor=ACCENT,
                            bulletFontSize=7, leftIndent=16)

    story: list = []

    # ---- Masthead ----
    story.append(Paragraph("POLICY IMPACT INTELLIGENCE&nbsp;&nbsp;·&nbsp;&nbsp;ANALYST BRIEFING", S["label"]))
    story.append(Paragraph(escape(pol.get("title", _POLICY_NAME)), S["title"]))
    meta_line = " &nbsp;·&nbsp; ".join(escape(x) for x in [
        pol.get("agency", ""), pol.get("docket_id", ""),
        pol.get("cfr_part", ""), pol.get("jurisdiction", ""),
    ] if x)
    story.append(Paragraph(meta_line, S["meta"]))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=6))

    # Provenance legend
    legend = "&nbsp;&nbsp;&nbsp;".join(
        f'<font color="{c}">■</font> {escape(lbl)}' for c, lbl in [
            ("#5B84B0", _PROV_LABELS["official"]),
            ("#4D8A72", _PROV_LABELS["opinion"]),
            ("#8B7045", _PROV_LABELS["reporting"]),
            ("#6B65A8", _PROV_LABELS["ai"]),
        ])
    story.append(Paragraph(legend, S["meta"]))
    story.append(Spacer(1, 8))

    # ---- Current status ----
    story.append(h2("Current Policy Status"))
    status_txt = f'<b>{escape(pol.get("status",""))}</b>'
    if pol.get("status_detail"):
        status_txt += " — " + escape(pol["status_detail"])
    story.append(Paragraph(status_txt, S["body"]))
    story.append(Paragraph(
        f'Analysis last generated: {escape(_fmt_dt(generated))} &nbsp;·&nbsp; '
        f'Exported: {escape(_fmt_dt(_now()))}', S["meta"]))

    # ---- Narrative sections ----
    if br.get("executive_summary"):
        story.append(h2("Executive Summary"))
        story.append(body(br["executive_summary"]))
    if br.get("policy_context"):
        story.append(h2("Policy Context"))
        story.append(body(br["policy_context"]))
    if br.get("key_policy_changes"):
        story.append(h2("Key Policy Changes"))
        story.append(bullets(br["key_policy_changes"]))

    pf = br.get("public_feedback") or {}
    if pf:
        story.append(h2("Public Feedback"))
        if pf.get("summary"):
            story.append(body(pf["summary"]))
        if pf.get("themes"):
            story.append(Spacer(1, 3))
            story.append(bullets(pf["themes"]))
        for v in pf.get("viewpoints", []):
            story.append(Paragraph(
                f'<b>{escape(v.get("label",""))}.</b> {escape(v.get("description",""))} '
                f'<font size="7" color="#5B6472">({escape(v.get("source",""))})</font>', S["body"]))

    nc = br.get("news_coverage") or {}
    if nc:
        story.append(h2("News Coverage"))
        if nc.get("summary"):
            story.append(body(nc["summary"]))
        if nc.get("developments"):
            story.append(Spacer(1, 3))
            story.append(bullets(nc["developments"]))

    # ---- Stakeholders table ----
    if br.get("stakeholders"):
        story.append(h2("Stakeholders"))
        data = [[Paragraph("Stakeholder", S["th"]),
                 Paragraph("Impact", S["th"]),
                 Paragraph("Assessment", S["th"])]]
        for s in br["stakeholders"]:
            impact = (s.get("impact") or "").lower()
            col = _IMPACT_COLORS.get(impact, "#5B6472")
            imp_p = Paragraph(f'<font color="{col}"><b>{escape(impact.title() or "—")}</b></font>', S["cell"])
            assess = escape(s.get("description", ""))
            src = ", ".join(s.get("sources", []))
            if src:
                assess += f'<br/><font size="7" color="#5B6472">Sources: {escape(src)}</font>'
            data.append([Paragraph(escape(s.get("group", "")), S["cell"]),
                         imp_p, Paragraph(assess, S["cell"])])
        tbl = Table(data, colWidths=[1.6 * inch, 0.85 * inch, 4.05 * inch], repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, RULE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BOXBG]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(tbl)

    if br.get("areas_of_alignment"):
        story.append(h2("Areas of Alignment"))
        story.append(bullets(br["areas_of_alignment"]))
    if br.get("areas_of_difference"):
        story.append(h2("Areas of Difference"))
        story.append(bullets(br["areas_of_difference"]))
    if br.get("uncertainties_and_limitations"):
        story.append(h2("Uncertainties & Limitations"))
        story.append(bullets(br["uncertainties_and_limitations"]))

    # ---- Sources / provenance ----
    if br.get("sources"):
        story.append(h2("Sources & Provenance"))
        for s in br["sources"]:
            prov = _SRC_PROV.get(s.get("type", ""), "ai")
            dot = {"official": "#5B84B0", "opinion": "#4D8A72",
                   "reporting": "#8B7045", "ai": "#6B65A8"}[prov]
            line = (f'<font color="{dot}">■</font> <b>{escape(s.get("label",""))}</b> '
                    f'<font size="7" color="#5B6472">({escape(_PROV_LABELS[prov])})</font> — '
                    f'{escape(s.get("description",""))}')
            if s.get("url"):
                line += f' <font size="7" color="#5B84B0">{escape(s["url"])}</font>'
            story.append(Paragraph(line, S["body"]))

    # ---- Disclaimer ----
    disclaimer = (br.get("_metadata", {}) or {}).get("disclaimer") or (
        "This briefing is AI-generated from limited data sources. It is a starting point "
        "for analysis, not a legal interpretation. Human analyst review is required before "
        "use in official communications."
    )
    story.append(Spacer(1, 12))
    box = Table([[Paragraph("<b>Disclaimer.</b> " + escape(disclaimer), S["discl"])]],
                colWidths=[6.5 * inch])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BOXBG),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(box)

    def _decor(canvas, doc):
        canvas.saveState()
        w, _h = LETTER
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(0.9 * inch, 0.68 * inch, w - 0.9 * inch, 0.68 * inch)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(0.9 * inch, 0.52 * inch,
                          "Policy Impact Intelligence  ·  AI-generated — analyst review required")
        canvas.drawRightString(w - 0.9 * inch, 0.52 * inch, f"Page {doc.page}")
        canvas.restoreState()

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch,
        topMargin=0.85 * inch, bottomMargin=0.9 * inch,
        title=f'{pol.get("title", "")} — Analyst Briefing',
        author="Policy Impact Intelligence",
    )
    doc.build(story, onFirstPage=_decor, onLaterPages=_decor)
    return buf.getvalue()


@app.get("/api/export/briefing.pdf")
def export_briefing_pdf(policy: Optional[str] = Query(None)):
    """Professional analyst briefing PDF for the selected policy."""
    pol, briefing, generated = _export_bundle(policy)
    try:
        pdf = _build_briefing_pdf(pol, briefing, generated)
    except ImportError:
        raise HTTPException(status_code=503,
                            detail="PDF generation is unavailable (reportlab not installed).")
    headers = {"Content-Disposition": f'attachment; filename="{pol["id"]}-analyst-briefing.pdf"'}
    return Response(content=pdf, media_type="application/pdf", headers=headers)
