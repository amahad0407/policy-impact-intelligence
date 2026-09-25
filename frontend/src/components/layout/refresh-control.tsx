'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { RefreshCw, Loader2, Check, AlertTriangle } from 'lucide-react';
import { fetchDataStatus, refreshData, type DataStatus } from '@/lib/api';

function relTime(iso: string | null): string {
  if (!iso) return '—';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '—';
  const min = Math.floor((Date.now() - then) / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return `${min} min ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function absTime(iso: string | null): string {
  if (!iso) return 'unknown';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 'unknown';
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' });
}

type Phase = 'idle' | 'checking' | 'analyzing' | 'done' | 'error';

export function RefreshControl() {
  const router = useRouter();
  const [status, setStatus] = useState<DataStatus | null>(null);
  const [phase, setPhase] = useState<Phase>('idle');
  const [message, setMessage] = useState<string>('');

  const loadStatus = useCallback(async () => {
    const s = await fetchDataStatus();
    setStatus(s);
  }, []);

  useEffect(() => { loadStatus(); }, [loadStatus]);

  async function onRefresh() {
    if (phase === 'checking' || phase === 'analyzing') return;
    setPhase('checking');
    setMessage('Checking sources…');
    try {
      const result = await refreshData();
      if (result.analysis_rerun.length > 0) {
        setPhase('analyzing');
        setMessage('Updating analysis…');
      }
      await loadStatus();
      if (result.errors.length > 0) {
        setPhase('error');
        setMessage(result.errors[0].slice(0, 80));
      } else if (result.changed) {
        setPhase('done');
        setMessage(result.new_articles > 0 ? `Updated · ${result.new_articles} new` : 'Updated');
        router.refresh();
      } else {
        setPhase('done');
        setMessage('Current · no changes');
      }
      setTimeout(() => { setPhase('idle'); setMessage(''); }, 4000);
    } catch (e) {
      setPhase('error');
      setMessage(e instanceof Error ? e.message.slice(0, 80) : 'Refresh failed');
      setTimeout(() => { setPhase('idle'); setMessage(''); }, 5000);
    }
  }

  const busy = phase === 'checking' || phase === 'analyzing';
  const updated = status?.analysis_last_generated ?? null;
  const lastChecked = status?.last_checked ?? null;

  return (
    <div className="flex items-center gap-2.5 shrink-0">
      {/* Last updated indicator (dynamic, from backend) */}
      <div
        className="hidden md:flex flex-col items-end leading-tight"
        title={`Analysis generated: ${absTime(updated)}\nSources last checked: ${lastChecked ? absTime(lastChecked) : 'not yet checked'}`}
      >
        <span className="text-[9.5px] font-medium uppercase tracking-[0.09em] text-[#4B5260]">Data updated</span>
        <span className="font-mono text-[10.5px] text-[#8B97AF]">{relTime(updated)}</span>
      </div>

      {/* Refresh button */}
      <button
        onClick={onRefresh}
        disabled={busy}
        title="Check sources and refresh analysis"
        className="flex h-6 items-center gap-1.5 rounded-[2px] border border-[#1C2028] bg-transparent px-2 text-[12px] transition-colors hover:border-[#252A31] disabled:cursor-not-allowed"
        style={{
          color: phase === 'error' ? '#C87070'
               : phase === 'done'  ? '#4D8A72'
               : busy              ? '#8B97AF'
               : '#6B7280',
        }}
      >
        {busy ? (
          <Loader2 className="h-3 w-3 animate-spin-slow" />
        ) : phase === 'done' ? (
          <Check className="h-3 w-3" />
        ) : phase === 'error' ? (
          <AlertTriangle className="h-3 w-3" />
        ) : (
          <RefreshCw className="h-3 w-3" />
        )}
        <span className="whitespace-nowrap">{message || 'Refresh'}</span>
      </button>
    </div>
  );
}
