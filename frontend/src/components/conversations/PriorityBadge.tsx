import type { ConversationPriorityLevel } from '../../types/conversation';

const LEVEL_CLASS: Record<ConversationPriorityLevel, string> = {
  urgent: 'priority-badge priority-badge--urgent',
  high: 'priority-badge priority-badge--high',
  medium: 'priority-badge priority-badge--medium',
  low: 'priority-badge priority-badge--low',
};

interface PriorityBadgeProps {
  level?: ConversationPriorityLevel | null;
  score?: number | null;
  reason?: string | null;
}

export function PriorityBadge({ level = 'low', score, reason }: PriorityBadgeProps) {
  const resolvedLevel = level ?? 'low';
  return (
    <span className={LEVEL_CLASS[resolvedLevel]} title={reason ?? undefined}>
      {resolvedLevel}
      {score != null ? ` (${score})` : ''}
    </span>
  );
}
