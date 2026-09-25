import type { Stakeholder } from '@/types';
import {
  Users,
  Briefcase,
  Building2,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';

const impactConfig = {
  positive: {
    label: 'Positive',
    className: 'text-emerald-400 bg-emerald-500/10',
    Icon: TrendingUp,
  },
  negative: {
    label: 'Negative',
    className: 'text-red-400 bg-red-500/10',
    Icon: TrendingDown,
  },
  mixed: {
    label: 'Mixed',
    className: 'text-amber-400 bg-amber-500/10',
    Icon: Minus,
  },
  neutral: {
    label: 'Neutral',
    className: 'text-zinc-400 bg-zinc-500/10',
    Icon: Minus,
  },
};

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  workers: Users,
  'senior-executives': Briefcase,
  'small-businesses': Building2,
  'large-employers': Building2,
  healthcare: Users,
  'virginia-workers': Users,
};

interface StakeholderCardProps {
  stakeholder: Stakeholder;
}

export function StakeholderCard({ stakeholder }: StakeholderCardProps) {
  const impact = impactConfig[stakeholder.impact];
  const ImpactIcon = impact.Icon;
  const GroupIcon = iconMap[stakeholder.id] ?? Users;

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="rounded-md bg-white/5 p-1.5">
            <GroupIcon className="h-4 w-4 text-zinc-400" />
          </div>
          <span className="text-sm font-medium text-foreground">
            {stakeholder.name}
          </span>
        </div>
        <span
          className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium shrink-0 ${impact.className}`}
        >
          <ImpactIcon className="h-3 w-3" />
          {impact.label}
        </span>
      </div>

      <p className="mt-2 text-xs leading-5 text-muted-foreground">
        {stakeholder.description}
      </p>

      {stakeholder.affectedCount && (
        <p className="mt-2 text-xs font-medium text-zinc-500">
          Scale: {stakeholder.affectedCount}
        </p>
      )}
    </div>
  );
}
