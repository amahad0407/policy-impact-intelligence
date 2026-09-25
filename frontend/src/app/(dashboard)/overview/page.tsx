import { fetchOverview, toStakeholder, toFinding } from '@/lib/api';
import { statsData, currentPolicy } from '@/lib/placeholder-data';
import { ProvLabel, ProvDot } from '@/components/shared/source-badge';
import { FindingCard } from '@/components/dashboard/finding-card';

export default async function OverviewPage() {
  const data = await fetchOverview();
  const stakeholders = data ? data.affected_stakeholders.map(toStakeholder) : [];
  const findings = data ? data.findings.map(toFinding) : [];

  return (
    <div className="max-w-[1360px] px-[clamp(16px,2.4vw,28px)] py-6 flex flex-col gap-8">

      {/* Page title + action buttons */}
      <div className="flex flex-col gap-3.5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="m-0 text-[22px] font-semibold tracking-[-0.01em] leading-[1.2] text-[#DFE1E6]">
              FTC Non-Compete Clause Rule
            </h1>
            <div className="font-mono text-[12px] text-[#6B7280]">16 CFR Part 910 · Federal Trade Commission</div>
          </div>
          <div className="flex gap-1.5 shrink-0">
            <a href="/comparison" className="flex h-[28px] items-center rounded-[2px] border border-[#1C2028] bg-transparent px-3 text-[12.5px] text-[#DFE1E6] no-underline hover:bg-[#131619]">Compare versions</a>
            <a href="/briefing" className="flex h-[28px] items-center rounded-[2px] border border-[#DFE1E6] bg-[#DFE1E6] px-3 text-[12.5px] font-medium text-[#0D0F12] no-underline hover:bg-white">Open briefing</a>
          </div>
        </div>

        {/* Metadata strip */}
        <div className="grid border-t border-b border-[#1C2028]" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))' }}>
          {[
            { k: 'Status',        v: 'Set aside (vacated)' },
            { k: 'Docket',        v: currentPolicy.docketId },
            { k: 'Proposed',      v: 'Jan 19, 2023' },
            { k: 'Final rule',    v: currentPolicy.publishedDate },
            { k: 'Document type', v: currentPolicy.documentType },
            { k: 'Pages',         v: String(currentPolicy.pageCount) },
          ].map(({ k, v }) => (
            <div key={k} className="flex flex-col gap-[3px] py-[9px] pr-[14px]">
              <span className="text-[11px] text-[#4B5260]">{k}</span>
              <span className="font-mono text-[12px] text-[#C8CAD0]">{v}</span>
            </div>
          ))}
        </div>

        {/* Stat strip */}
        <div className="grid border-b border-[#1C2028]" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))' }}>
          {statsData.map(s => (
            <div key={s.label} className="flex flex-col gap-[3px] py-[9px] pr-[14px]">
              <span className="text-[11px] text-[#4B5260]">{s.label}</span>
              <span className="font-mono text-[12px] text-[#C8CAD0]">{s.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Court-vacated notice */}
      <div className="ds-panel flex items-start gap-[10px] px-3 py-[10px] text-[13px] leading-[1.5] text-[#7A8090]">
        <span className="shrink-0 text-[#C87070] mt-[1px]">!</span>
        <span><span className="font-medium text-[#DFE1E6]">Court action.</span> On Aug 20, 2024, the U.S. District Court for the Northern District of Texas set aside this rule nationwide. It is not currently in effect.</span>
      </div>

      {!data && (
        <div className="ds-panel flex items-start gap-[10px] p-4">
          <span className="mt-[1px] text-[#C87070]">!</span>
          <div>
            <div className="text-[14px] font-medium text-[#DFE1E6]">Analysis not available</div>
            <div className="mt-1 text-[13px] leading-[1.5] text-[#7A8090]">
              Start the backend: <code className="font-mono text-[12px]">uvicorn app.main:app --port 8000</code>
            </div>
          </div>
        </div>
      )}

      {data && (
        <>
          {/* Summary */}
          <section className="flex flex-col gap-3">
            <div className="ds-section-head">
              <h2 className="m-0 text-[14px] font-semibold text-[#DFE1E6]">Summary</h2>
              <ProvLabel type="ai" />
            </div>
            <p className="m-0 max-w-[820px] text-[13.5px] leading-[1.65] text-[#C8CAD0]">{data.policy_summary}</p>
          </section>

          {/* Key Changes */}
          {data.key_changes.length > 0 && (
            <section className="flex flex-col">
              <div className="ds-section-head">
                <h2 className="m-0 text-[14px] font-semibold text-[#DFE1E6]">
                  Key Changes <span className="text-[12px] font-normal text-[#4B5260]">{data.key_changes.length} provisions</span>
                </h2>
                <a href="/comparison" className="border-none bg-none p-0 text-[12.5px] text-[#6B65A8] cursor-pointer hover:underline no-underline">Full comparison</a>
              </div>
              {data.key_changes.map((c, i) => (
                <div key={i} className="ds-row grid gap-[10px] py-[9px] text-[13.5px] leading-[1.5]" style={{ gridTemplateColumns: '24px 1fr' }}>
                  <span className="font-mono text-[12px] text-[#4B5260] pt-[2px]">{String(i + 1).padStart(2, '0')}</span>
                  <span className="text-[#C8CAD0]">{c}</span>
                </div>
              ))}
            </section>
          )}

          {/* Stakeholders table */}
          {stakeholders.length > 0 && (
            <section className="flex flex-col">
              <div className="ds-section-head">
                <h2 className="m-0 text-[14px] font-semibold text-[#DFE1E6]">
                  Stakeholders <span className="text-[12px] font-normal text-[#4B5260]">{stakeholders.length} identified</span>
                </h2>
                <span className="text-[11px] text-[#4B5260]">Across all sources</span>
              </div>
              <div className="overflow-x-auto">
                <div style={{ minWidth: 600 }}>
                  <div className="ds-row grid gap-4 py-2" style={{ gridTemplateColumns: '200px 1fr 90px' }}>
                    <span className="text-[11px] font-medium uppercase tracking-[0.07em] text-[#4B5260]">Stakeholder</span>
                    <span className="text-[11px] font-medium uppercase tracking-[0.07em] text-[#4B5260]">Impact</span>
                    <span className="text-[11px] font-medium uppercase tracking-[0.07em] text-[#4B5260]">Source</span>
                  </div>
                  {stakeholders.map(s => (
                    <div key={s.id} className="ds-row grid gap-4 py-[9px] items-start hover:bg-[#131619]" style={{ gridTemplateColumns: '200px 1fr 90px' }}>
                      <span className="text-[13.5px] font-medium text-[#C8CAD0]">{s.name}</span>
                      <span className="text-[13.5px] text-[#7A8090]">{s.description}</span>
                      <span className={`text-[12.5px] capitalize ${s.impact === 'positive' ? 'text-[#4D8A72]' : s.impact === 'negative' ? 'text-[#C87070]' : 'text-[#8B7045]'}`}>{s.impact}</span>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* Key Findings */}
          {findings.length > 0 && (
            <section className="flex flex-col">
              <div className="ds-section-head">
                <h2 className="m-0 text-[14px] font-semibold text-[#DFE1E6]">Key Findings</h2>
              </div>
              {findings.map((f, i) => <FindingCard key={f.id} finding={f} index={i} />)}
            </section>
          )}

          {/* Uncertainties */}
          {data.uncertainty_or_limitations.length > 0 && (
            <section className="flex flex-col">
              <div className="ds-section-head">
                <h2 className="m-0 text-[14px] font-semibold text-[#DFE1E6]">Uncertainties &amp; Limitations</h2>
                <ProvLabel type="ai" />
              </div>
              <div className="ds-panel">
                {data.uncertainty_or_limitations.map((l, i) => (
                  <div key={i} className="border-b border-[#181C22] px-[14px] py-[9px] last:border-0">
                    <div className="text-[13px] leading-[1.5] text-[#7A8090]">{l}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Key Definitions */}
          {data.important_definitions.length > 0 && (
            <section className="flex flex-col">
              <div className="ds-section-head">
                <h2 className="m-0 text-[14px] font-semibold text-[#DFE1E6]">Key Definitions</h2>
                <ProvLabel type="official" />
              </div>
              <div className="overflow-x-auto">
                <div style={{ minWidth: 500 }}>
                  {data.important_definitions.map((d, i) => (
                    <div key={i} className="ds-row grid gap-4 py-[9px]" style={{ gridTemplateColumns: '180px 1fr' }}>
                      <span className="font-mono text-[12px] text-[#C8CAD0]">&ldquo;{d.term}&rdquo;</span>
                      <span className="text-[13px] text-[#7A8090] leading-[1.5]">{d.definition}</span>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* Sources table */}
          <section className="flex flex-col" id="src">
            <div className="ds-section-head">
              <h2 className="m-0 text-[14px] font-semibold text-[#DFE1E6]">Sources</h2>
              <span className="text-[11px] text-[#4B5260]">{data._metadata.source_documents.length} primary</span>
            </div>
            <div className="overflow-x-auto">
              <div style={{ minWidth: 500 }}>
                <div className="ds-row grid gap-4 py-2" style={{ gridTemplateColumns: '32px 1fr 160px 140px' }}>
                  <span className="text-[11px] font-medium uppercase tracking-[0.07em] text-[#4B5260]">#</span>
                  <span className="text-[11px] font-medium uppercase tracking-[0.07em] text-[#4B5260]">Document</span>
                  <span className="text-[11px] font-medium uppercase tracking-[0.07em] text-[#4B5260]">Provenance</span>
                  <span className="text-[11px] font-medium uppercase tracking-[0.07em] text-[#4B5260]">Date</span>
                </div>
                {data._metadata.source_documents.map((s, i) => (
                  <div key={i} className="ds-row grid gap-4 py-[9px] items-center hover:bg-[#131619]" style={{ gridTemplateColumns: '32px 1fr 160px 140px' }}>
                    <span className="font-mono text-[12px] text-[#4B5260]">[{i + 1}]</span>
                    <a href={s.source_url} target="_blank" rel="noopener noreferrer" className="truncate text-[13.5px] text-[#C8CAD0] no-underline hover:underline">{s.label}</a>
                    <ProvLabel type="official" />
                    <span className="font-mono text-[12px] text-[#6B7280]">{s.publication_date}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <div className="font-mono text-[11px] text-[#4B5260] border-t border-[#1C2028] pt-3">
            Generated by {data._metadata.deployment} · {new Date(data._metadata.generated_at).toLocaleDateString()}
          </div>
        </>
      )}
    </div>
  );
}
