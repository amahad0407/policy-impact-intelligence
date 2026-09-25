'use client';

import { useState } from 'react';
import type { Finding } from '@/types';
import { ProvDot, ProvLabel } from '@/components/shared/source-badge';

const CONF = {
  high:   { label: 'High confidence',   color: '#4D8A72' },
  medium: { label: 'Medium confidence', color: '#8B7045' },
  low:    { label: 'Low confidence',    color: '#C87070' },
};

export function FindingCard({ finding, index }: { finding: Finding; index: number }) {
  const [open, setOpen] = useState(false);
  const conf = CONF[finding.confidence];

  return (
    <div className="ds-row grid gap-[10px] py-3" style={{ gridTemplateColumns: '24px 1fr' }}>
      <span className="font-mono text-[12px] text-[#4B5260] pt-[2px]">{String(index + 1).padStart(2, '0')}</span>
      <div className="flex flex-col gap-1.5">
        <div className="flex flex-wrap items-center gap-3">
          <ProvLabel type={finding.sourceType} />
          <span className="text-[12.5px]" style={{ color: conf.color }}>· {conf.label}</span>
        </div>
        <div className="text-[13.5px] leading-[1.55] text-[#DFE1E6]">{finding.claim}</div>
        <button
          onClick={() => setOpen(v => !v)}
          className="self-start border-none bg-transparent p-0 text-[12.5px] cursor-pointer text-[#6B7280] hover:text-[#8B97AF] transition-colors"
        >
          {open ? '↑ Hide evidence' : `↓ View evidence (${finding.evidence.length})`}
        </button>
        {open && (
          <div className="flex flex-col gap-2 mt-1">
            {finding.evidence.map(ev => (
              <div key={ev.id} className="ds-panel px-3 py-2.5">
                <div className="flex items-center gap-2 mb-1.5">
                  <ProvDot type={ev.sourceType} />
                  <span className="text-[12px] text-[#4B5260]">{ev.sourceDocument}</span>
                </div>
                <p className="m-0 text-[13px] italic leading-[1.55] text-[#C8CAD0]">&ldquo;{ev.excerpt}&rdquo;</p>
                {ev.sourceUrl && (
                  <a href={ev.sourceUrl} target="_blank" rel="noopener noreferrer" className="mt-1 text-[12px] text-[#6B65A8] no-underline hover:underline block">↗ Source</a>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
