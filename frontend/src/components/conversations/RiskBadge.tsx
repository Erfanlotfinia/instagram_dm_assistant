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

export function RiskBadge({ level, score }: RiskBadgeProps) {
  const normalized = level ?? 'unknown';
  return (
    <span className={`status-pill status-pill--${normalized}`} aria-label={`Risk level ${normalized}`}>
      {LABELS[normalized] ?? 'Risk unknown'}{typeof score === 'number' ? ` · ${Math.round(score * 100)}%` : ''}
    </span>
  );
}
