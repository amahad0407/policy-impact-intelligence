'use client';

import { usePathname } from 'next/navigation';
import { RefreshControl } from './refresh-control';
import { SearchCommand } from './search-command';
import { ExportControl } from './export-control';

const CRUMBS: Record<string, string> = {
  '/overview':   'Overview',
  '/feedback':   'Public Feedback',
  '/news':       'News Coverage',
  '/comparison': 'Policy Comparison',
  '/briefing':   'Analyst Briefing',
  '/analyze':    'Analyze Policy',
};

export function Header() {
  const pathname = usePathname();
  const crumb = CRUMBS[pathname] ?? '';

  return (
    <header className="flex h-[40px] shrink-0 items-center justify-between gap-4 border-b border-[#181D24] bg-[#0D0F12] px-[clamp(12px,2vw,24px)]">
      {/* Policy + page breadcrumb */}
      <div className="flex items-center gap-2 text-[12.5px] min-w-0">
        <span className="text-[#4B5260] truncate">FTC Non-Compete Rule</span>
        <span className="text-[#2E3440]">/</span>
        <span className="text-[#8B97AF] font-medium">{crumb}</span>
      </div>

      {/* Search + Refresh + Export */}
      <div className="flex items-center gap-1.5 shrink-0">
        <SearchCommand />
        <RefreshControl />
        <ExportControl />
      </div>
    </header>
  );
}
