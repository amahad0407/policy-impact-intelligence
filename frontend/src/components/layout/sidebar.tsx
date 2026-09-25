'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, MessageSquare, Newspaper,
  GitCompare, FileText, FlaskConical, Settings
} from 'lucide-react';
import { ProvDot } from '@/components/shared/source-badge';
import { PolicySelector } from './policy-selector';
import type { SourceType } from '@/types';

const NAV = [
  { href: '/overview',   label: 'Overview',          Icon: LayoutDashboard, meta: '' },
  { href: '/feedback',   label: 'Public Feedback',   Icon: MessageSquare,   meta: '26k' },
  { href: '/news',       label: 'News Coverage',     Icon: Newspaper,       meta: '48' },
  { href: '/comparison', label: 'Policy Comparison', Icon: GitCompare,      meta: '' },
  { href: '/briefing',   label: 'Analyst Briefing',  Icon: FileText,        meta: '' },
] as const;

const LEGEND: { type: SourceType | 'hypo'; label: string }[] = [
  { type: 'official',   label: 'Official Policy' },
  { type: 'opinion',    label: 'Public Opinion' },
  { type: 'reporting',  label: 'Factual Reporting' },
  { type: 'ai',         label: 'AI Interpretation' },
  { type: 'hypo',       label: 'Hypothetical' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="relative flex h-screen w-[216px] shrink-0 flex-col border-r border-[#181D24] bg-[#0B0D10]">
      {/* Brand mark */}
      <div className="flex h-[44px] shrink-0 items-center gap-2 border-b border-[#181D24] px-4">
        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-[2px] bg-[#4F5FD4]">
          <span className="h-[5px] w-[5px] rotate-45 bg-[#0B0D10]" />
        </span>
        <span className="text-[13px] font-semibold tracking-[0.01em] text-[#C8CAD0]">Policy Impact</span>
      </div>

      {/* Policy selector */}
      <PolicySelector />

      {/* Section label */}
      <div className="px-4 pt-4 pb-1 text-[10.5px] font-semibold uppercase tracking-[0.1em] text-[#4B5260]">
        Analysis
      </div>

      {/* Navigation */}
      <nav className="flex flex-col px-2">
        {NAV.map(({ href, label, Icon, meta }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className="relative flex h-[28px] items-center gap-2 px-2 text-[13.5px] no-underline transition-colors hover:bg-[#181D26]"
              style={{
                borderRadius: 2,
                background: active ? '#181D26' : 'transparent',
                color: active ? '#DFE1E6' : '#7A8090',
                fontWeight: active ? 500 : 400,
              }}
            >
              {active && (
                <span className="absolute left-0 top-1 bottom-1 w-[2px] rounded-full bg-[#4F5FD4]" />
              )}
              <Icon className="h-[13px] w-[13px] shrink-0" style={{ color: active ? '#8B97C8' : '#4B5260' }} />
              <span className="flex-1 truncate">{label}</span>
              {meta && <span className="font-mono text-[10.5px] text-[#4B5260]">{meta}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Tools section */}
      <div className="px-4 pt-4 pb-1 text-[10.5px] font-semibold uppercase tracking-[0.1em] text-[#4B5260]">
        Tools
      </div>
      <div className="px-2">
        <Link
          href="/analyze"
          className="relative flex h-[28px] w-full items-center gap-2 px-2 text-[13.5px] no-underline transition-colors hover:bg-[#181D26]"
          style={{
            borderRadius: 2,
            background: pathname === '/analyze' ? '#181D26' : 'transparent',
            color: pathname === '/analyze' ? '#DFE1E6' : '#7A8090',
            fontWeight: pathname === '/analyze' ? 500 : 400,
          }}
        >
          {pathname === '/analyze' && (
            <span className="absolute left-0 top-1 bottom-1 w-[2px] rounded-full bg-[#4F5FD4]" />
          )}
          <FlaskConical className="h-[13px] w-[13px] shrink-0 text-[#4F5FD4]" />
          <span>Analyze Policy</span>
        </Link>
      </div>

      <div className="flex-1" />

      {/* Provenance legend */}
      <div className="border-t border-[#181D24] px-4 py-3">
        <div className="mb-2 text-[10.5px] font-semibold uppercase tracking-[0.1em] text-[#4B5260]">Provenance</div>
        <div className="flex flex-col gap-1">
          {LEGEND.map(({ type, label }) => (
            <div key={type} className="flex items-center gap-2 text-[12px] text-[#7A8090]">
              <ProvDot type={type} />
              {label}
            </div>
          ))}
        </div>
      </div>

      {/* User row */}
      <div className="flex items-center gap-2 border-t border-[#181D24] px-4 py-2.5">
        <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-[#1A1E26] text-[9px] font-semibold text-[#7A8090]">
          JR
        </span>
        <div className="min-w-0 flex-1 text-[12px] leading-[1.3]">
          <div className="text-[#B8BCC8]">J. Rivera</div>
          <div className="text-[10.5px] text-[#4B5260]">Policy Analyst</div>
        </div>
        <Settings className="h-3 w-3 text-[#4B5260]" />
      </div>
    </aside>
  );
}
