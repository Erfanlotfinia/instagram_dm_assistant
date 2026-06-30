/**
 * Sprint 5 — Human Operator Workspace 2.0
 *
 * Operator-facing types for the prioritized queue, SLA, quick replies,
 * customer timeline, and workload panels. These are pure UI-layer types
 * derived from existing conversation / handoff / order / decision-trace data.
 */

export type OperatorQueueStatus =
  | 'needs_attention'
  | 'waiting_customer'
  | 'waiting_operator'
  | 'assigned'
  | 'unassigned'
  | 'resolved'
  | 'escalated';

export type OperatorConversationPriority = 'urgent' | 'high' | 'normal' | 'low';

export type OperatorSlaState = 'within_sla' | 'approaching_breach' | 'breached' | 'unknown';

export interface OperatorSlaRule {
  id: string;
  label: string;
  target_minutes: number;
  priority: OperatorConversationPriority;
  enabled: boolean;
}

export type QuickReplyCategory =
  | 'greeting'
  | 'price'
  | 'stock'
  | 'payment'
  | 'shipping'
  | 'handoff'
  | 'recovery'
  | 'custom';

export interface QuickReplyTemplate {
  id: string;
  title: string;
  category: QuickReplyCategory;
  body: string;
  variables: string[];
  enabled: boolean;
}

export interface OperatorReplyDraft {
  conversation_id: string;
  source: 'quick_reply' | 'suggested_reply' | 'manual';
  body: string;
  variables_resolved: Record<string, string>;
  warnings: string[];
  requires_approval: boolean;
}

export type CustomerTimelineItemType =
  | 'message'
  | 'order'
  | 'payment'
  | 'handoff'
  | 'ai_decision'
  | 'note'
  | 'system';

export interface CustomerTimelineItem {
  id: string;
  type: CustomerTimelineItemType;
  title: string;
  description?: string | null;
  created_at?: string | null;
  action_to?: string;
}

export interface OperatorQueueItem {
  conversation_id: string;
  customer_label: string;
  channel_provider?: string | null;
  channel_account_label?: string | null;
  assigned_operator_id?: string | null;
  assigned_operator_name?: string | null;
  status: OperatorQueueStatus;
  priority: OperatorConversationPriority;
  sla_state: OperatorSlaState;
  last_message_preview?: string | null;
  last_inbound_at?: string | null;
  last_outbound_at?: string | null;
  waiting_minutes?: number | null;
  unread_count?: number;
  handoff_reason?: string | null;
  ai_summary?: string | null;
  revenue_context?: string | null;
  action_to: string;
}

export interface OperatorWorkloadRow {
  operator_id: string;
  operator_name: string;
  assigned_count: number;
  breached_sla_count: number;
  resolved_today_count?: number;
  avg_response_minutes?: number | null;
  high_priority_count?: number;
}

export interface OperatorWorkspaceSummary {
  needs_attention_count: number;
  breached_sla_count: number;
  unassigned_count: number;
  assigned_to_me_count: number;
  high_priority_count: number;
  resolved_today_count?: number;
}

/**
 * Map the backend's `ConversationPriorityLevel` (`urgent|high|medium|low`) onto
 * the operator priority vocabulary, where `medium` is treated as `normal`.
 */
export function toOperatorPriority(
  level: 'urgent' | 'high' | 'medium' | 'low' | null | undefined,
): OperatorConversationPriority {
  if (level === 'urgent') return 'urgent';
  if (level === 'high') return 'high';
  if (level === 'low') return 'low';
  return 'normal';
}
