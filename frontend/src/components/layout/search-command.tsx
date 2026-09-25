'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Search, Loader2, X, ExternalLink } from 'lucide-react';
import { ProvDot } from '@/components/shared/source-badge';
import { searchEvidence, type SearchResult } from '@/lib/api';

function fmtDate(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

/**
 * Search Evidence — deterministic search over the app's processed data
 * (findings, comments, news, stakeholders, definitions, briefing, comparison…).
 * Opens from the header control or ⌘K. Never queries the internet or GPT.
 */
export function SearchCommand() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const close = useCallback(() => {
    setOpen(false);
    setQuery('');
    setResults([]);
    setSearched(false);
    abortRef.current?.abort();
  }, []);

  // ⌘K / Ctrl+K to open, Esc to close
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === 'Escape' && open) {
        close();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, close]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  // Debounced search
  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setResults([]);
      setSearched(false);
      setLoading(false);
      return;
    }
    setLoading(true);
    const handle = setTimeout(async () => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      const res = await searchEvidence(q, ctrl.signal);
      if (ctrl.signal.aborted) return;
      setResults(res.results);
      setSearched(true);
      setLoading(false);
    }, 180);
    return () => clearTimeout(handle);
  }, [query]);

  return (
    <>
      {/* Header trigger — visually identical to the original static control */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        title="Search evidence"
        className="hidden lg:flex h-6 cursor-pointer items-center gap-1.5 rounded-[2px] border border-[#1C2028] bg-[#0D0F12] px-2 text-[12px] text-[#4B5260] min-w-[160px] transition-colors hover:border-[#252A31] hover:text-[#6B7280]"
      >
        <Search className="h-3 w-3 shrink-0" />
        <span className="flex-1 text-left">Search evidence</span>
        <span className="font-mono text-[9.5px] text-[#2E3440]">⌘K</span>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[100] flex items-start justify-center px-4 pt-[12vh]"
          onMouseDown={close}
        >
          <div className="absolute inset-0 bg-black/55" />
          <div
            role="dialog"
            aria-label="Search evidence"
            onMouseDown={(e) => e.stopPropagation()}
            className="relative z-10 flex max-h-[70vh] w-full max-w-[620px] flex-col overflow-hidden rounded-[3px] border border-[#252A31] bg-[#0D0F12] shadow-[0_16px_48px_rgba(0,0,0,0.6)]"
          >
            {/* Input */}
            <div className="flex items-center gap-2 border-b border-[#181D24] px-3 py-2.5">
              {loading ? (
                <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin-slow text-[#4B5260]" />
              ) : (
                <Search className="h-3.5 w-3.5 shrink-0 text-[#4B5260]" />
              )}
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search evidence — policy, comments, news, stakeholders…"
                className="flex-1 bg-transparent text-[13px] text-[#DFE1E6] placeholder:text-[#4B5260] outline-none"
              />
              <button
                type="button"
                onClick={close}
                className="flex h-5 w-5 items-center justify-center rounded-[2px] text-[#4B5260] transition-colors hover:text-[#8B97AF]"
                aria-label="Close search"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>

            {/* Results */}
            <div className="min-h-0 flex-1 overflow-y-auto">
              {!query.trim() && (
                <div className="px-4 py-6 text-[12px] leading-relaxed text-[#4B5260]">
                  Search across the FTC Non-Compete Rule evidence base — official policy
                  language, public comments, news coverage, stakeholders, definitions, key
                  changes, comparison and briefing findings. Results stay within processed
                  data; nothing leaves the system.
                </div>
              )}

              {query.trim() && searched && results.length === 0 && !loading && (
                <div className="px-4 py-6 text-[12.5px] text-[#8B97AF]">
                  No evidence found for{' '}
                  <span className="font-medium text-[#DFE1E6]">“{query.trim()}”</span>.
                  <div className="mt-1 text-[11.5px] text-[#4B5260]">
                    Try a broader term such as “non-compete”, “workers”, or “senior executives”.
                  </div>
                </div>
              )}

              {results.length > 0 && (
                <>
                  <div className="px-4 pt-2.5 pb-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-[#4B5260]">
                    {results.length} result{results.length === 1 ? '' : 's'}
                  </div>
                  <ul className="pb-2">
                    {results.map((r) => {
                      const meta = [r.source, fmtDate(r.date), r.policy].filter(Boolean).join(' · ');
                      const Row = r.url ? 'a' : 'div';
                      return (
                        <li key={r.id}>
                          <Row
                            {...(r.url
                              ? { href: r.url, target: '_blank', rel: 'noopener noreferrer' }
                              : {})}
                            className={`group flex flex-col gap-1 border-b border-[#131619] px-4 py-2.5 no-underline ${
                              r.url ? 'cursor-pointer hover:bg-[#131619]' : ''
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <ProvDot type={r.provenance} />
                              <span className="text-[10px] font-medium uppercase tracking-[0.07em] text-[#5B6472]">
                                {r.provenance_label}
                              </span>
                              <span className="text-[#2E3440]">·</span>
                              <span className="text-[10px] uppercase tracking-[0.05em] text-[#4B5260]">
                                {r.category}
                              </span>
                              {r.url && (
                                <ExternalLink className="ml-auto h-3 w-3 text-[#2E3440] group-hover:text-[#6B7280]" />
                              )}
                            </div>
                            <div className="text-[12.5px] font-medium leading-snug text-[#DFE1E6]">
                              {r.title}
                            </div>
                            <div className="line-clamp-2 text-[11.5px] leading-relaxed text-[#8B97AF]">
                              {r.excerpt}
                            </div>
                            {meta && (
                              <div className="truncate font-mono text-[10px] text-[#4B5260]">
                                {meta}
                              </div>
                            )}
                          </Row>
                        </li>
                      );
                    })}
                  </ul>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
