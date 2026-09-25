import type { SourceType } from '@/types';

export const PROV = {
  official: { label: 'Official Policy',   fill: '#5B84B0', border: '#5B84B0' },
  opinion:  { label: 'Public Opinion',    fill: '#4D8A72', border: '#4D8A72' },
  reporting:{ label: 'Factual Reporting', fill: '#8B7045', border: '#8B7045' },
  ai:       { label: 'AI Interpretation', fill: 'transparent', border: '#6B65A8' },
  hypo:     { label: 'Hypothetical',      fill: 'transparent', border: '#4F5FD4', dashed: true },
} as const;

type ProvKey = keyof typeof PROV;

/** 7×7 square provenance dot */
export function ProvDot({ type }: { type: SourceType | 'hypo' }) {
  const p = PROV[type as ProvKey] ?? PROV.ai;
  return (
    <span
      style={{
        display: 'inline-block',
        width: 7,
        height: 7,
        borderRadius: 1,
        background: p.fill,
        border: `1px ${(p as { dashed?: boolean }).dashed ? 'dashed' : 'solid'} ${p.border}`,
        flexShrink: 0,
      }}
    />
  );
}

/** Inline provenance label with dot */
export function ProvLabel({ type, className = '' }: { type: SourceType | 'hypo'; className?: string }) {
  const p = PROV[type as ProvKey] ?? PROV.ai;
  return (
    <span className={`inline-flex items-center gap-[6px] text-[12.5px] text-[#8B97AF] ${className}`}>
      <ProvDot type={type} />
      {p.label}
    </span>
  );
}

// ── Legacy alias kept for page compatibility ──────────────────────────────

interface SourceBadgeProps { type: SourceType; className?: string; }

export function SourceBadge({ type, className = '' }: SourceBadgeProps) {
  return <ProvLabel type={type} className={className} />;
}

export function SourceLegend() {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-2">
      {(['official', 'opinion', 'reporting', 'ai'] as SourceType[]).map(t => (
        <ProvLabel key={t} type={t} />
      ))}
    </div>
  );
}
