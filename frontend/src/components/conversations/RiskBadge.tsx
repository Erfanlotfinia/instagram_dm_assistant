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
  // Avoid surfacing an "unknown" badge as visual noise before risk is scored.
  if (!level || !LABELS[level]) {
    return null;
  }
  return (
    <span className={`status-pill status-pill--${level}`} aria-label={`Risk level ${level}`}>
      {LABELS[level]}{typeof score === 'number' ? ` · ${Math.round(score * 100)}%` : ''}
    </span>
  );
}
