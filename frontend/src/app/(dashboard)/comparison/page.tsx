import { fetchComparison } from '@/lib/api';
import { ProvLabel } from '@/components/shared/source-badge';

export default async function ComparisonPage() {
  const data = await fetchComparison();

  return (
    <div className="max-w-[1360px] px-[clamp(16px,2.4vw,28px)] py-6 flex flex-col gap-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="m-0 text-[22px] font-semibold tracking-[-0.01em] leading-[1.2] text-[#DFE1E6]">Policy Comparison</h1>
          <div className="flex flex-wrap items-center gap-2 text-[13.5px] text-[#7A8090]">
            <ProvLabel type="official" />
            <span className="text-[#4B5260]">·</span>
            <span>Proposed Rule vs. Final Rule</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-4 text-[12.5px] text-[#7A8090]">
          <span className="flex items-center gap-1.5"><span className="inline-block h-[10px] w-[14px] bg-[rgba(91,132,176,0.2)]" />Changed</span>
          <span className="flex items-center gap-1.5"><span className="inline-block h-[10px] w-[14px] bg-[rgba(77,138,114,0.2)]" />Added</span>
          <span className="flex items-center gap-1.5"><span className="inline-block h-[10px] w-[14px] bg-[rgba(200,112,112,0.2)]" /><span className="line-through">Removed</span></span>
        </div>
      </div>

      {!data && (
        <div className="ds-panel flex items-start gap-[10px] p-4">
          <span className="text-[#C87070] mt-[1px]">!</span>
          <div>
            <div className="text-[14px] font-medium text-[#DFE1E6]">Comparison not available</div>
            <div className="mt-1 text-[13px] text-[#7A8090]">Run <code className="font-mono text-[12px]">python scripts/analyze_comparison.py</code></div>
          </div>
        </div>
      )}

      {data && (
        <>
          {data._metadata.disclaimer && (
            <div className="ds-panel flex items-start gap-[10px] px-3 py-[10px] text-[13px] leading-[1.5] text-[#7A8090]">
              <span className="mt-[2px] shrink-0">i</span>
              <span>{data._metadata.disclaimer}</span>
            </div>
          )}

          <section className="flex flex-col gap-3">
            <div className="ds-section-head">
              <h2 className="m-0 text-[14px] font-semibold text-[#DFE1E6]">Summary</h2>
              <ProvLabel type="ai" />
            </div>
            <p className="m-0 max-w-[820px] text-[13.5px] leading-[1.65] text-[#C8CAD0]">{data.summary}</p>
          </section>

          {/* Diff table */}
          <section>
            <div className="ds-section-head mb-0">
              <h2 className="m-0 text-[14px] font-semibold text-[#DFE1E6]">
                What Changed <span className="text-[12px] font-normal text-[#4B5260]">{data.key_changes.length} topics</span>
              </h2>
            </div>
            <div className="ds-panel overflow-hidden">
              <div className="overflow-x-auto">
                <div style={{ minWidth: 820 }}>
                  <div className="grid border-b border-[#1C2028] bg-[#131619]" style={{ gridTemplateColumns: '200px 1fr 1fr 90px' }}>
                    <div className="px-[14px] py-[9px] text-[11px] font-medium uppercase tracking-[0.07em] text-[#4B5260] self-end">Provision</div>
                    <div className="border-l border-[#1C2028] px-[14px] py-[9px]">
                      <div className="text-[13.5px] font-semibold text-[#DFE1E6]">Proposed Rule</div>
                      <div className="font-mono text-[11px] text-[#4B5260] mt-[2px]">88 FR 3482 · 2023-01-19</div>
                    </div>
                    <div className="border-l border-[#1C2028] px-[14px] py-[9px]">
                      <div className="text-[13.5px] font-semibold text-[#DFE1E6]">Final Rule</div>
                      <div className="font-mono text-[11px] text-[#4B5260] mt-[2px]">89 FR 38342 · 2024-05-07</div>
                    </div>
                    <div className="border-l border-[#1C2028] px-[14px] py-[9px] text-[11px] font-medium uppercase tracking-[0.07em] text-[#4B5260] self-end">Change</div>
                  </div>
                  {data.key_changes.length > 0 && (
                    <div className="border-b border-[#181C22] bg-[#0D0F12] px-[14px] py-2 text-[11px] font-semibold tracking-[.08em] text-[#4B5260]">KEY CHANGES</div>
                  )}
                  {data.key_changes.map((c, i) => (
                    <div key={i} className="grid border-b border-[#181C22] text-[13.5px] leading-[1.55]" style={{ gridTemplateColumns: '200px 1fr 1fr 90px' }}>
                      <div className="px-[14px] py-[9px] font-medium text-[#DFE1E6]">{c.topic}</div>
                      <div className="border-l border-[#181C22] px-[14px] py-[9px] text-[#7A8090]">{c.proposed}</div>
                      <div className="border-l border-[#181C22] px-[14px] py-[9px] text-[#DFE1E6]">{c.final}</div>
                      <div className="border-l border-[#181C22] px-[14px] py-[9px] text-[12.5px] text-[#5B84B0]">Changed</div>
                    </div>
                  ))}
                  {data.definitions.length > 0 && (
                    <div className="border-b border-[#181C22] bg-[#0D0F12] px-[14px] py-2 text-[11px] font-semibold tracking-[.08em] text-[#4B5260]">DEFINITIONS</div>
                  )}
                  {data.definitions.map((d, i) => (
                    <div key={i} className="grid border-b border-[#181C22] text-[13.5px] leading-[1.55]" style={{ gridTemplateColumns: '200px 1fr 1fr 90px' }}>
                      <div className="px-[14px] py-[9px] font-mono text-[12px] text-[#DFE1E6]">&ldquo;{d.term}&rdquo;</div>
                      <div className="border-l border-[#181C22] px-[14px] py-[9px] text-[#7A8090]">{d.proposed_definition}</div>
                      <div className="border-l border-[#181C22] px-[14px] py-[9px] text-[#DFE1E6]">{d.final_definition}</div>
                      <div className="border-l border-[#181C22] px-[14px] py-[9px] text-[12.5px] text-[#6B7280]">{d.changed ? 'Changed' : 'Same'}</div>
                    </div>
                  ))}
                  {data.unchanged_elements.length > 0 && (
                    <div className="border-b border-[#181C22] bg-[#0D0F12] px-[14px] py-2 text-[11px] font-semibold tracking-[.08em] text-[#4B5260]">UNCHANGED ELEMENTS</div>
                  )}
                  {data.unchanged_elements.map((u, i) => (
                    <div key={i} className="grid border-b border-[#181C22] last:border-0 text-[13.5px] leading-[1.55]" style={{ gridTemplateColumns: '200px 2fr 90px' }}>
                      <div className="px-[14px] py-[9px] text-[#C8CAD0]">{u}</div>
                      <div className="border-l border-[#181C22] px-[14px] py-[9px] text-[#7A8090]">{u}</div>
                      <div className="border-l border-[#181C22] px-[14px] py-[9px] text-[12.5px] text-[#4B5260]">Unchanged</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <div className="grid gap-8" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,440px),1fr))' }}>
            {data.timeline.length > 0 && (
              <section className="flex flex-col">
                <div className="ds-section-head">
                  <h2 className="m-0 text-[14px] font-semibold text-[#DFE1E6]">Timeline</h2>
                </div>
                {data.timeline.map((t, i) => (
                  <div key={i} className="ds-row grid gap-3 py-2" style={{ gridTemplateColumns: '96px 70px 1fr' }}>
                    <span className="font-mono text-[12px] text-[#4B5260]">{t.date}</span>
                    <span className="text-[13px] text-[#7A8090]">{t.document}</span>
                    <span className="text-[13.5px] text-[#DFE1E6]">{t.event}</span>
                  </div>
                ))}
              </section>
            )}
            {data.sources.length > 0 && (
              <section className="flex flex-col">
                <div className="ds-section-head">
                  <h2 className="m-0 text-[14px] font-semibold text-[#DFE1E6]">Sources</h2>
                </div>
                {data.sources.map((s, i) => (
                  <div key={i} className="ds-row grid gap-3 py-2 items-center" style={{ gridTemplateColumns: '32px 1fr auto' }}>
                    <span className="font-mono text-[12px] text-[#4B5260]">[{i + 1}]</span>
                    <span className="text-[13.5px] text-[#DFE1E6]">{s.label} <span className="font-mono text-[12px] text-[#4B5260]">{s.document_number}</span></span>
                    <ProvLabel type="official" />
                  </div>
                ))}
              </section>
            )}
          </div>

          {data.limitations.length > 0 && (
            <section className="flex flex-col">
              <div className="ds-section-head">
                <h2 className="m-0 text-[14px] font-semibold text-[#DFE1E6]">Limitations</h2>
                <ProvLabel type="ai" />
              </div>
              <div className="ds-panel">
                {data.limitations.map((l, i) => (
                  <div key={i} className="border-b border-[#181C22] px-[14px] py-[9px] last:border-0 text-[13px] leading-[1.5] text-[#7A8090]">{l}</div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
