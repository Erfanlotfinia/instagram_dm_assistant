import type { ConversationPriorityLevel } from '../../types/conversation';

import { Badge, type BadgeTone } from '../ui';

const LEVEL_TONE: Record<ConversationPriorityLevel, BadgeTone> = {
  urgent: 'danger',
  high: 'warning',
  medium: 'accent',
  low: 'neutral',
};

const LEVEL_LABEL: Record<ConversationPriorityLevel, string> = {
  urgent: 'Urgent',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
};

interface PriorityBadgeProps {
  level?: ConversationPriorityLevel | null;
  score?: number | null;
  reason?: string | null;
}

export function PriorityBadge({ level = 'low', score, reason }: PriorityBadgeProps) {
  const resolvedLevel = level ?? 'low';
  return (
    <Badge tone={LEVEL_TONE[resolvedLevel]} title={reason ?? undefined} aria-label={`Priority: ${LEVEL_LABEL[resolvedLevel]}`}>
      {LEVEL_LABEL[resolvedLevel]}
      {score != null ? ` (${score})` : ''}
    </Badge>
  );
}
