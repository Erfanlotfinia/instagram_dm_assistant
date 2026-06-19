import { Badge, type BadgeTone } from '../ui';

interface RiskBadgeProps {
  level?: string | null;
  score?: number | null;
}

const LABELS: Record<string, string> = {
  low: 'Low risk',
  medium: 'Medium risk',
  high: 'High risk',
  critical: 'Critical risk',
};

const TONES: Record<string, BadgeTone> = {
  low: 'success',
  medium: 'warning',
  high: 'danger',
  critical: 'danger',
};

export function RiskBadge({ level, score }: RiskBadgeProps) {
  if (!level || !LABELS[level]) {
    return null;
  }
  return (
    <Badge tone={TONES[level] ?? 'neutral'} aria-label={`Risk level ${level}`}>
      {LABELS[level]}
      {typeof score === 'number' ? ` · ${Math.round(score * 100)}%` : ''}
    </Badge>
  );
}
