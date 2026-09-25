'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ChevronsUpDown, Check, FlaskConical } from 'lucide-react';
import { fetchPolicies, type Policy } from '@/lib/api';

const STORAGE_KEY = 'pii.selectedPolicyId';

/**
 * Functional policy selector for the sidebar.
 * - Lists policies that actually exist in the system (from /api/policies).
 * - Persists the selection in localStorage so it survives navigation.
 * - "Analyze New Policy" routes to /analyze.
 * Only one real policy exists today; the mechanism is ready for more.
 */
export function PolicySelector() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let mounted = true;
    fetchPolicies().then((list) => {
      if (!mounted) return;
      setPolicies(list);
      const stored = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
      const active = list.find((p) => p.id === stored) ?? list.find((p) => p.is_active) ?? list[0];
      if (active) setSelectedId(active.id);
    });
    return () => { mounted = false; };
  }, []);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  const selected = policies.find((p) => p.id === selectedId) ?? null;

  function choose(id: string) {
    setSelectedId(id);
    try { localStorage.setItem(STORAGE_KEY, id); } catch { /* ignore */ }
    setOpen(false);
  }

  return (
    <div ref={ref} className="relative border-b border-[#181D24] px-3 py-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 rounded-[2px] px-1.5 py-1.5 text-left transition-colors hover:bg-[#181D26]"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <div className="min-w-0 flex-1">
          <div className="text-[10.5px] font-medium uppercase tracking-[0.08em] text-[#4B5260]">Policy</div>
          <div className="truncate text-[13px] text-[#B8BCC8]">
            {selected?.short_title ?? 'FTC Non-Compete Rule'}
          </div>
        </div>
        <ChevronsUpDown className="h-3 w-3 shrink-0 text-[#4B5260]" />
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute left-3 right-3 top-[calc(100%-4px)] z-50 overflow-hidden rounded-[2px] border border-[#252A31] bg-[#131619] shadow-[0_8px_24px_rgba(0,0,0,0.5)]"
        >
          <div className="px-2.5 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-[#4B5260]">
            Policies
          </div>
          {policies.map((p) => {
            const active = p.id === selectedId;
            return (
              <button
                key={p.id}
                role="option"
                aria-selected={active}
                onClick={() => choose(p.id)}
                className="flex w-full items-start gap-2 px-2.5 py-2 text-left transition-colors hover:bg-[#181D26]"
              >
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[12.5px] text-[#DFE1E6]">{p.short_title}</div>
                  <div className="mt-0.5 truncate font-mono text-[10.5px] text-[#4B5260]">
                    {p.docket_id} · {p.status}
                  </div>
                </div>
                {active && <Check className="mt-0.5 h-3 w-3 shrink-0 text-[#6B65A8]" />}
              </button>
            );
          })}
          {policies.length === 0 && (
            <div className="px-2.5 py-2 text-[12px] text-[#4B5260]">No policies available</div>
          )}

          <div className="border-t border-[#252A31]">
            <Link
              href="/analyze"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2 px-2.5 py-2 text-[12.5px] text-[#8B97AF] no-underline transition-colors hover:bg-[#181D26] hover:text-[#DFE1E6]"
            >
              <FlaskConical className="h-3 w-3 shrink-0 text-[#4F5FD4]" />
              Analyze New Policy
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
