import type { ReactNode } from 'react';

import { Icons } from '../icons';
import { Sparkline } from './Sparkline';
import { cn } from '../../lib/cn';

type Tone = 'accent' | 'success' | 'warning' | 'danger';

interface KpiCardProps {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  /** Percentage delta vs previous period. Positive renders as up/green. */
  delta?: number | null;
  /** Inverts delta colors (e.g. fallback rate going down is good). */
  invertDelta?: boolean;
  trend?: number[];
  tone?: Tone;
  to?: string;
}

function DeltaPill({ delta, invert }: { delta: number; invert: boolean }) {
  const positive = delta >= 0;
  const good = invert ? !positive : positive;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-xs font-medium',
        good ? 'bg-success-soft text-success' : 'bg-danger-soft text-danger',
      )}
    >
      {positive ? <Icons.arrowUpRight size={12} /> : <Icons.arrowDownRight size={12} />}
      {Math.abs(delta).toFixed(1)}%
    </span>
  );
}

export function KpiCard({
  label,
  value,
  hint,
  delta,
  invertDelta = false,
  trend,
  tone = 'accent',
}: KpiCardProps) {
  return (
    <div className="cc-themed flex flex-col justify-between rounded-[var(--radius-card)] border border-border bg-surface p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium text-muted">{label}</p>
        {typeof delta === 'number' ? <DeltaPill delta={delta} invert={invertDelta} /> : null}
      </div>
      <div className="mt-2 flex items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="text-2xl font-semibold tabular-nums text-fg">{value}</p>
          {hint ? <p className="mt-0.5 truncate text-xs text-subtle">{hint}</p> : null}
        </div>
        {trend && trend.length > 1 ? <Sparkline data={trend} tone={tone} /> : null}
      </div>
    </div>
  );
}
