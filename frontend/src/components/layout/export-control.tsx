'use client';

import { useEffect, useRef, useState } from 'react';
import { Download, Loader2, FileText, Braces, AlertTriangle } from 'lucide-react';
import { downloadExport } from '@/lib/api';

// Same key the policy selector persists to, so exports track the current policy.
const STORAGE_KEY = 'pii.selectedPolicyId';

type Kind = 'pdf' | 'json';

/**
 * Export control — downloads the currently selected policy's analyst briefing
 * as a professional PDF, or its structured data as JSON. Generation happens
 * on the backend; no credentials are ever exposed to the client.
 */
export function ExportControl() {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<Kind | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  async function run(kind: Kind) {
    if (busy) return;
    setBusy(kind);
    setError(null);
    setOpen(false);
    const policyId =
      typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    try {
      await downloadExport(kind, policyId);
    } catch (e) {
      setError(e instanceof Error ? e.message.slice(0, 60) : 'Export failed');
      setTimeout(() => setError(null), 5000);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={!!busy}
        title="Export analyst briefing"
        className="flex h-6 cursor-pointer items-center gap-1 rounded-[2px] border border-[#1C2028] bg-transparent px-2 text-[12px] transition-colors hover:border-[#252A31] hover:text-[#9CA3AF] disabled:cursor-not-allowed"
        style={{ color: error ? '#C87070' : busy ? '#8B97AF' : '#6B7280' }}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        {busy ? (
          <Loader2 className="h-3 w-3 animate-spin-slow" />
        ) : error ? (
          <AlertTriangle className="h-3 w-3" />
        ) : (
          <Download className="h-3 w-3" />
        )}
        <span className="whitespace-nowrap">
          {busy ? 'Exporting…' : error ? error : 'Export'}
        </span>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-[calc(100%+4px)] z-50 w-[212px] overflow-hidden rounded-[2px] border border-[#252A31] bg-[#131619] shadow-[0_8px_24px_rgba(0,0,0,0.5)]"
        >
          <div className="px-2.5 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-[#4B5260]">
            Export current policy
          </div>
          <button
            type="button"
            role="menuitem"
            onClick={() => run('pdf')}
            className="flex w-full items-start gap-2 px-2.5 py-2 text-left transition-colors hover:bg-[#181D26]"
          >
            <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#5B84B0]" />
            <div className="min-w-0">
              <div className="text-[12.5px] text-[#DFE1E6]">Analyst Briefing (PDF)</div>
              <div className="text-[10.5px] text-[#4B5260]">Formatted government-style briefing</div>
            </div>
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => run('json')}
            className="flex w-full items-start gap-2 border-t border-[#20262E] px-2.5 py-2 text-left transition-colors hover:bg-[#181D26]"
          >
            <Braces className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#6B65A8]" />
            <div className="min-w-0">
              <div className="text-[12.5px] text-[#DFE1E6]">Data (JSON)</div>
              <div className="text-[10.5px] text-[#4B5260]">Structured briefing with provenance</div>
            </div>
          </button>
        </div>
      )}
    </div>
  );
}
