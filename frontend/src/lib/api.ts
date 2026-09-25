import type { PolicyAnalysis, ApiStakeholder, ApiFinding } from '@/types/api';
import type { Finding, Stakeholder } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function fetchOverview(): Promise<PolicyAnalysis | null> {
  try {
    const res = await fetch(`${API_BASE}/api/overview`, {
      next: { revalidate: 0 }, // always fresh during development
    });
    if (!res.ok) return null;
    return res.json() as Promise<PolicyAnalysis>;
  } catch {
    return null;
  }
}

// Transform API stakeholder → frontend Stakeholder component shape
export function toStakeholder(s: ApiStakeholder, index: number): Stakeholder {
  return {
    id: `api-s${index}`,
    name: s.group,
    description: s.description,
    impact: s.impact,
    scale: s.source_document,
    affectedCount: undefined,
  };
}

// Transform API finding → frontend Finding component shape
export function toFinding(f: ApiFinding, index: number): Finding {
  return {
    id: `api-f${index}`,
    claim: f.claim,
    sourceType: f.source_type,
    confidence: f.confidence,
    evidence: f.evidence.map((e, ei) => ({
      id: `api-f${index}-e${ei}`,
      excerpt: e.excerpt,
      sourceType: f.source_type,
      sourceDocument: e.source_section
        ? `${e.source_document} — ${e.source_section}`
        : e.source_document,
    })),
  };
}

import type { CommentsAnalysis } from '@/types/api';

export async function fetchFeedback(): Promise<CommentsAnalysis | null> {
  try {
    const res = await fetch(`${API_BASE}/api/feedback`, {
      next: { revalidate: 0 },
    });
    if (!res.ok) return null;
    return res.json() as Promise<CommentsAnalysis>;
  } catch {
    return null;
  }
}

import type { NewsAnalysis } from '@/types/api';

export async function fetchNews(): Promise<NewsAnalysis | null> {
  try {
    const res = await fetch(`${API_BASE}/api/news`, { next: { revalidate: 0 } });
    if (!res.ok) return null;
    return res.json() as Promise<NewsAnalysis>;
  } catch {
    return null;
  }
}

import type { BriefingAnalysis } from '@/types/api';

export async function fetchBriefing(): Promise<BriefingAnalysis | null> {
  try {
    const res = await fetch(`${API_BASE}/api/briefing`, { next: { revalidate: 0 } });
    if (!res.ok) return null;
    return res.json() as Promise<BriefingAnalysis>;
  } catch {
    return null;
  }
}

import type { ComparisonAnalysis } from '@/types/api';

export async function fetchComparison(): Promise<ComparisonAnalysis | null> {
  try {
    const res = await fetch(`${API_BASE}/api/comparison`, { next: { revalidate: 0 } });
    if (!res.ok) return null;
    return res.json() as Promise<ComparisonAnalysis>;
  } catch {
    return null;
  }
}

// ── Policy registry / freshness / refresh (client-callable) ─────────────────

export interface Policy {
  id: string;
  title: string;
  short_title: string;
  agency: string;
  docket_id: string;
  cfr_part: string;
  status: string;
  status_detail: string;
  jurisdiction: string;
  generated_at: string | null;
  is_active: boolean;
}

export interface DataStatus {
  analysis_last_generated: string | null;
  last_checked: string | null;
  sources: {
    federal_register: { last_checked: string | null; kind: string; note?: string };
    news: { last_checked: string | null; kind: string; latest_article_date: string | null; article_count: number };
    comments: { last_checked: string | null; kind: string; note?: string };
  };
}

export interface RefreshResult {
  started_at: string;
  sources_checked: string[];
  sources_updated: string[];
  analysis_rerun: string[];
  errors: string[];
  changed: boolean;
  new_articles: number;
  completed_at: string | null;
  note: string;
}

export async function fetchPolicies(): Promise<Policy[]> {
  try {
    const res = await fetch(`${API_BASE}/api/policies`, { cache: 'no-store' });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.policies ?? []) as Policy[];
  } catch {
    return [];
  }
}

export async function fetchDataStatus(): Promise<DataStatus | null> {
  try {
    const res = await fetch(`${API_BASE}/api/status`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json() as Promise<DataStatus>;
  } catch {
    return null;
  }
}

export async function refreshData(): Promise<RefreshResult> {
  const res = await fetch(`${API_BASE}/api/refresh`, { method: 'POST' });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? `Refresh failed (${res.status})`);
  }
  return res.json() as Promise<RefreshResult>;
}

// ── Evidence search (deterministic search over processed data) ───────────────

export type ProvenanceKey = 'official' | 'opinion' | 'reporting' | 'ai';

export interface SearchResult {
  id: string;
  category: string;
  provenance: ProvenanceKey;
  provenance_label: string;
  title: string;
  excerpt: string;
  date: string | null;
  source: string | null;
  policy: string;
  url: string | null;
}

export interface SearchResponse {
  query: string;
  count: number;
  results: SearchResult[];
}

export async function searchEvidence(q: string, signal?: AbortSignal): Promise<SearchResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(q)}`, {
      cache: 'no-store',
      signal,
    });
    if (!res.ok) return { query: q, count: 0, results: [] };
    return res.json() as Promise<SearchResponse>;
  } catch {
    return { query: q, count: 0, results: [] };
  }
}

// ── Export (analyst briefing PDF / structured JSON) ──────────────────────────

/** Fetch an export as a Blob so the browser downloads it with a clean filename. */
export async function downloadExport(kind: 'pdf' | 'json', policyId: string | null): Promise<void> {
  const q = policyId ? `?policy=${encodeURIComponent(policyId)}` : '';
  const res = await fetch(`${API_BASE}/api/export/briefing.${kind}${q}`, { cache: 'no-store' });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? `Export failed (${res.status})`);
  }
  const disposition = res.headers.get('content-disposition') ?? '';
  const match = disposition.match(/filename="?([^"]+)"?/i);
  const filename = match?.[1] ?? `briefing.${kind}`;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
