import { Badge } from '../ui';
import type { BadgeTone } from '../ui';
import type { Conversation } from '../../types/conversation';

export type AutomationStatus = 'automated' | 'llm' | 'human' | 'preview';

interface StatusMeta {
  label: string;
  tone: BadgeTone;
}

const STATUS_META: Record<AutomationStatus, StatusMeta> = {
  automated: { label: 'Automated', tone: 'success' },
  llm: { label: 'LLM handled', tone: 'info' },
  preview: { label: 'Preview', tone: 'warning' },
  human: { label: 'Human required', tone: 'danger' },
};

/**
 * Derives the operator-facing automation status from conversation flags.
 * Mirrors the audit-trail policy: handoff/paused => human, preview => awaiting
 * review of an LLM draft, low confidence => LLM handled, else automated.
 */
export function getAutomationStatus(conversation: Pick<
  Conversation,
  'handoff_required' | 'agent_paused' | 'workflow_state' | 'preview_required' | 'confidence_score' | 'agent_mode'
>): AutomationStatus {
  if (conversation.handoff_required || conversation.agent_paused || conversation.workflow_state === 'human_handoff') {
    return 'human';
  }
  if (conversation.preview_required) {
    return 'preview';
  }
  if (conversation.agent_mode === 'human_first') {
    return 'human';
  }
  if (typeof conversation.confidence_score === 'number' && conversation.confidence_score < 0.7) {
    return 'llm';
  }
  return 'automated';
}

export function AutomationStatusBadge({
  conversation,
}: {
  conversation: Parameters<typeof getAutomationStatus>[0];
}) {
  const status = getAutomationStatus(conversation);
  const meta = STATUS_META[status];
  return (
    <Badge tone={meta.tone} dot>
      {meta.label}
    </Badge>
  );
}
