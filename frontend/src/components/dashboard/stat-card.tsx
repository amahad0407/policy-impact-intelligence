import type { StatCardData } from '@/types';

interface StatCardProps extends StatCardData {
  icon: React.ReactNode;
}

export function StatCard({ label, value, description, icon }: StatCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <p className="mt-1 text-2xl font-semibold text-foreground">{value}</p>
        </div>
        <div className="rounded-md bg-violet-500/10 p-2 text-violet-400">{icon}</div>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">{description}</p>
    </div>
  );
}
