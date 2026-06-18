import { cn } from '../../lib/cn';
import { confidenceBandTone } from '../../lib/confidenceBand';

interface ScoreBarProps {
  value: number;
  band: string;
  className?: string;
}

const fillTones: Record<string, string> = {
  high: 'bg-success',
  success: 'bg-success',
  medium: 'bg-warning',
  warning: 'bg-warning',
  low: 'bg-danger',
  danger: 'bg-danger',
};

export function ScoreBar({ value, band, className }: ScoreBarProps) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  const tone = confidenceBandTone(band);
  const fill = fillTones[band] ?? (tone === 'success' ? 'bg-success' : tone === 'warning' ? 'bg-warning' : tone === 'danger' ? 'bg-danger' : 'bg-accent');

  return (
    <div
      className={cn('h-1.5 overflow-hidden rounded-full bg-surface-sunken', className)}
      role="img"
      aria-label={`${pct}% match`}
    >
      <div className={cn('h-full rounded-full transition-all', fill)} style={{ width: `${pct}%` }} />
    </div>
  );
}
