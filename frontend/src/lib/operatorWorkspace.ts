/**
 * Sprint 5 — pure deterministic operator workspace builders.
 *
 * No React, no network. All functions accept partial data and return useful
 * partial output so the operator workspace can render even when some sources
 * (decision traces, orders, customer profile) are unavailable.
 */
import type {
  AgentDecisionTrace,
  Conversation,
  ConversationDetail,
  ConversationEvent,
  CustomerProfile,
  Message,
} from '../types/conversation';
import type { Order } from '../types/order';
import type {
  CustomerTimelineItem,
  OperatorConversationPriority,
  OperatorQueueItem,
  OperatorQueueStatus,
  OperatorReplyDraft,
  OperatorSlaRule,
  OperatorSlaState,
  OperatorWorkspaceSummary,
  OperatorWorkloadRow,
  QuickReplyTemplate,
} from '../types/sprint5Operator';
import { toOperatorPriority } from '../types/sprint5Operator';

const DEFAULT_SLA_TARGETS: Record<OperatorConversationPriority, number> = {
  urgent: 15,
  high: 30,
  normal: 120,
  low: 240,
};

const PRIORITY_RANK: Record<OperatorConversationPriority, number> = {
  urgent: 0,
  high: 1,
  normal: 2,
  low: 3,
};

const QUICK_REPLY_VARIABLES = [
  'customer_name',
  'product_name',
  'order_id',
  'payment_link',
  'city',
  'channel_name',
] as const;

const MS_PER_MINUTE = 60_000;

export interface QueueBuildInput {
  conversations?: Conversation[] | null;
  decisionTraces?: AgentDecisionTrace[] | null;
  customers?: Record<string, CustomerProfile | null> | null;
  orders?: Order[] | null;
  revenueOpportunities?: Array<{ conversation_id?: string | null; label?: string | null }> | null;
  currentOperatorId?: string | null;
  slaRules?: OperatorSlaRule[] | null;
  now?: () => Date;
}

export interface PriorityInferenceInput {
  handoff_required?: boolean | null;
  risk_level?: 'low' | 'medium' | 'high' | 'critical' | null;
  waiting_minutes?: number | null;
  unpaid_order?: boolean | null;
  high_value_order?: boolean | null;
  repeat_customer?: boolean | null;
  revenue_opportunity?: boolean | null;
  priority_level?: 'urgent' | 'high' | 'medium' | 'low' | null;
}

export interface QuickReplyContext {
  customer_name?: string | null;
  product_name?: string | null;
  order_id?: string | null;
  payment_link?: string | null;
  city?: string | null;
  channel_name?: string | null;
}

export interface TimelineBuildInput {
  messages?: Message[] | null;
  events?: ConversationEvent[] | null;
  decisionTraces?: AgentDecisionTrace[] | null;
  orders?: Order[] | null;
  previousOrders?: Array<{ id: string; status: string; payment_status: string; created_at: string }> | null;
  conversationId?: string | null;
  shopId?: string | null;
}

/**
 * Minutes the customer has been waiting for an operator reply.
 * - null when there is no inbound timestamp to anchor on.
 * - 0 when the last outbound (operator action) is newer than the last inbound.
 * - otherwise minutes elapsed since the last inbound message.
 */
export function calculateWaitingMinutes(
  lastInboundAt: string | null | undefined,
  lastOutboundAt: string | null | undefined,
  now: Date = new Date(),
): number | null {
  if (!lastInboundAt) return null;
  const inboundMs = new Date(lastInboundAt).getTime();
  if (Number.isNaN(inboundMs)) return null;

  if (lastOutboundAt) {
    const outboundMs = new Date(lastOutboundAt).getTime();
    if (!Number.isNaN(outboundMs) && outboundMs >= inboundMs) {
      return 0;
    }
  }
  const diff = now.getTime() - inboundMs;
  if (diff < 0) return 0;
  return Math.floor(diff / MS_PER_MINUTE);
}

function slaTargetFor(
  priority: OperatorConversationPriority,
  rules?: OperatorSlaRule[] | null,
): number {
  if (rules && rules.length > 0) {
    const enabled = rules.find((r) => r.enabled && r.priority === priority);
    if (enabled) return enabled.target_minutes;
  }
  return DEFAULT_SLA_TARGETS[priority];
}

export function calculateSlaState(
  waitingMinutes: number | null | undefined,
  priority: OperatorConversationPriority,
  rules?: OperatorSlaRule[] | null,
): OperatorSlaState {
  if (waitingMinutes == null) return 'unknown';
  const target = slaTargetFor(priority, rules);
  if (waitingMinutes >= target) return 'breached';
  if (waitingMinutes >= target * 0.8) return 'approaching_breach';
  return 'within_sla';
}

/**
 * Deterministic priority inference. Higher-severity signals win.
 * Does not call any LLM; purely rule-based.
 */
export function inferOperatorPriority(input: PriorityInferenceInput): OperatorConversationPriority {
  if (input.handoff_required && input.risk_level === 'critical') return 'urgent';
  if (input.risk_level === 'critical') return 'urgent';
  if (input.handoff_required && input.waiting_minutes != null && input.waiting_minutes >= 30) {
    return 'urgent';
  }

  if (input.risk_level === 'high') return 'high';
  if (input.high_value_order) return 'high';
  if (input.handoff_required && input.unpaid_order) return 'high';
  if (input.handoff_required && input.repeat_customer) return 'high';
  if (input.revenue_opportunity) return 'high';

  if (input.handoff_required) return 'high';
  if (input.waiting_minutes != null && input.waiting_minutes >= 60) return 'high';

  if (input.priority_level === 'urgent') return 'urgent';
  if (input.priority_level === 'high') return 'high';
  if (input.priority_level === 'low') return 'low';

  return 'normal';
}

function customerLabel(conversation: Conversation): string {
  return (
    conversation.customer?.full_name ??
    conversation.customer?.instagram_user_id ??
    conversation.customer_id.slice(0, 8)
  );
}

function deriveQueueStatus(conversation: Conversation): OperatorQueueStatus {
  if (conversation.state === 'closed' || conversation.state === 'archived') return 'resolved';
  if (conversation.workflow_state === 'human_handoff') return 'escalated';
  if (conversation.needs_attention) return 'needs_attention';
  if (conversation.assigned_operator_id) return 'assigned';
  if (conversation.handoff_required) return 'unassigned';

  const waiting = calculateWaitingMinutes(
    conversation.last_message_at,
    conversation.last_operator_action_at,
  );
  if (waiting != null && waiting > 0) {
    // Customer is waiting on a reply.
    return conversation.last_message_direction === 'inbound' ? 'waiting_operator' : 'waiting_customer';
  }
  return 'waiting_customer';
}

function latestTraceForConversation(
  traces: AgentDecisionTrace[] | null | undefined,
  conversationId: string,
): AgentDecisionTrace | null {
  if (!traces || traces.length === 0) return null;
  const forConv = traces.filter((t) => t.conversation_id === conversationId);
  if (forConv.length === 0) return null;
  return forConv.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
}

function aiSummaryFor(
  conversation: Conversation,
  traces: AgentDecisionTrace[] | null,
): string | null {
  const trace = latestTraceForConversation(traces, conversation.id);
  return trace?.reasoning_summary ?? null;
}

function revenueContextFor(
  conversation: Conversation,
  orders: Order[] | null,
  opportunities: QueueBuildInput['revenueOpportunities'],
): string | null {
  const linkedOrder = conversation.linked_order;
  if (linkedOrder) {
    const payment = linkedOrder.payment_status ?? '—';
    const status = linkedOrder.status ?? '—';
    return `Order ${linkedOrder.id.slice(0, 8)} · ${status} · ${payment}`;
  }
  if (orders) {
    const match = orders.find((o) => o.conversation_id === conversation.id);
    if (match) {
      return `Order ${match.id.slice(0, 8)} · ${match.status} · ${match.payment_status}`;
    }
  }
  if (opportunities) {
    const match = opportunities.find((o) => o.conversation_id === conversation.id);
    if (match?.label) return match.label;
  }
  return null;
}

/**
 * Build the prioritized operator queue. Dedupes by conversation_id, computes
 * SLA + status, and sorts by: breached SLA → urgent/high → unassigned handoff
 * → newest inbound message.
 */
export function buildOperatorQueueItems(input: QueueBuildInput): OperatorQueueItem[] {
  const conversations = input.conversations ?? [];
  if (conversations.length === 0) return [];

  const now = input.now ? input.now() : new Date();
  const traces = input.decisionTraces ?? null;
  const orders = input.orders ?? null;
  const opportunities = input.revenueOpportunities ?? null;

  const byId = new Map<string, OperatorQueueItem>();
  for (const conversation of conversations) {
    if (byId.has(conversation.id)) continue;

    const lastInboundAt = conversation.last_message_at ?? null;
    const lastOutboundAt = conversation.last_operator_action_at ?? null;
    const waitingMinutes = calculateWaitingMinutes(lastInboundAt, lastOutboundAt, now);

    const trace = latestTraceForConversation(traces, conversation.id);
    const priority = inferOperatorPriority({
      handoff_required: conversation.handoff_required,
      risk_level: trace?.risk_score?.risk_level ?? null,
      waiting_minutes: waitingMinutes,
      unpaid_order: conversation.linked_order?.payment_status === 'unpaid' || conversation.linked_order?.payment_status === 'pending',
      high_value_order: null,
      repeat_customer: input.customers?.[conversation.customer_id]?.is_repeat_customer ?? null,
      revenue_opportunity: Boolean(opportunities?.some((o) => o.conversation_id === conversation.id)),
      priority_level: conversation.priority_level ?? null,
    });

    const slaState = calculateSlaState(waitingMinutes, priority, input.slaRules ?? null);
    const status = deriveQueueStatus(conversation);

    byId.set(conversation.id, {
      conversation_id: conversation.id,
      customer_label: customerLabel(conversation),
      channel_provider: conversation.channel_provider ?? null,
      channel_account_label: null,
      assigned_operator_id: conversation.assigned_operator_id ?? null,
      assigned_operator_name: conversation.assigned_operator?.full_name ?? null,
      status,
      priority,
      sla_state: slaState,
      last_message_preview: conversation.last_message_text ?? null,
      last_inbound_at: lastInboundAt,
      last_outbound_at: lastOutboundAt,
      waiting_minutes: waitingMinutes,
      unread_count: 0,
      handoff_reason: conversation.handoff_reason ?? null,
      ai_summary: aiSummaryFor(conversation, traces),
      revenue_context: revenueContextFor(conversation, orders, opportunities),
      action_to: `/inbox/${conversation.id}`,
    });
  }

  const items = Array.from(byId.values());
  items.sort((a, b) => {
    const slaRank: Record<OperatorSlaState, number> = {
      breached: 0,
      approaching_breach: 1,
      within_sla: 2,
      unknown: 3,
    };
    const slaDiff = slaRank[a.sla_state] - slaRank[b.sla_state];
    if (slaDiff !== 0) return slaDiff;

    const prioDiff = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
    if (prioDiff !== 0) return prioDiff;

    const aUnassignedHandoff = a.status === 'unassigned' ? 0 : 1;
    const bUnassignedHandoff = b.status === 'unassigned' ? 0 : 1;
    if (aUnassignedHandoff !== bUnassignedHandoff) return aUnassignedHandoff - bUnassignedHandoff;

    const aInbound = a.last_inbound_at ? new Date(a.last_inbound_at).getTime() : 0;
    const bInbound = b.last_inbound_at ? new Date(b.last_inbound_at).getTime() : 0;
    return bInbound - aInbound;
  });

  return items;
}

/**
 * Build a unified customer timeline (newest first) from existing message,
 * order, payment, handoff, decision-trace, and note data. No backend mutation.
 */
export function buildCustomerTimeline(input: TimelineBuildInput): CustomerTimelineItem[] {
  const items: CustomerTimelineItem[] = [];
  const conversationId = input.conversationId ?? null;
  const shopId = input.shopId ?? null;

  for (const message of input.messages ?? []) {
    if (message.message_type === 'system') {
      items.push({
        id: `msg:${message.id}`,
        type: 'system',
        title: message.text ?? 'System message',
        created_at: message.created_at,
      });
      continue;
    }
    items.push({
      id: `msg:${message.id}`,
      type: 'message',
      title: message.direction === 'inbound' ? 'Customer message' : 'Operator message',
      description: message.text,
      created_at: message.created_at,
    });
  }

  for (const event of input.events ?? []) {
    const type: CustomerTimelineItem['type'] =
      event.event_type === 'handoff_required' || event.event_type === 'operator_took_over' || event.event_type === 'operator_released_to_agent' || event.event_type === 'conversation_assigned'
        ? 'handoff'
        : event.event_type === 'payment_link_sent' || event.event_type === 'payment_received'
          ? 'payment'
          : event.event_type.startsWith('suggested_reply')
            ? 'ai_decision'
            : 'system';
    items.push({
      id: `evt:${event.id}`,
      type,
      title: event.title,
      description: event.description,
      created_at: event.created_at,
    });
  }

  for (const trace of input.decisionTraces ?? []) {
    if (conversationId && trace.conversation_id !== conversationId) continue;
    items.push({
      id: `trace:${trace.id}`,
      type: 'ai_decision',
      title: trace.intent ? `AI decision · ${trace.intent}` : 'AI decision',
      description: trace.reasoning_summary,
      created_at: trace.created_at,
      action_to: conversationId && shopId ? `/inbox/${conversationId}/intelligence` : undefined,
    });
  }

  for (const order of input.orders ?? []) {
    if (conversationId && order.conversation_id !== conversationId) continue;
    items.push({
      id: `order:${order.id}`,
      type: 'order',
      title: `Order ${order.id.slice(0, 8)} · ${order.status}`,
      description: `${order.total_amount} ${order.currency} · ${order.payment_status}`,
      created_at: order.created_at,
      action_to: shopId ? `/orders/${order.id}` : undefined,
    });
  }

  for (const order of input.previousOrders ?? []) {
    items.push({
      id: `prev-order:${order.id}`,
      type: 'order',
      title: `Previous order ${order.id.slice(0, 8)} · ${order.status}`,
      description: `Payment: ${order.payment_status}`,
      created_at: order.created_at,
    });
  }

  items.sort((a, b) => {
    const aMs = a.created_at ? new Date(a.created_at).getTime() : 0;
    const bMs = b.created_at ? new Date(b.created_at).getTime() : 0;
    return bMs - aMs;
  });

  return items;
}

/**
 * Render a quick reply template into an OperatorReplyDraft, substituting
 * variables. Unresolved variables remain visible as `{{var}}` and are listed
 * in `warnings`. Drafts always require operator approval before sending.
 */
export function renderQuickReply(
  template: QuickReplyTemplate,
  context: QuickReplyContext,
  conversationId = '',
): OperatorReplyDraft {
  const resolved: Record<string, string> = {};
  const warnings: string[] = [];
  let body = template.body;

  for (const variable of QUICK_REPLY_VARIABLES) {
    const value = context[variable] ?? null;
    const placeholder = `{{${variable}}}`;
    if (value) {
      resolved[variable] = value;
      body = body.split(placeholder).join(value);
    } else if (template.variables.includes(variable) && body.includes(placeholder)) {
      warnings.push(`Unresolved variable: ${variable}`);
    }
  }

  return {
    conversation_id: conversationId,
    source: 'quick_reply',
    body,
    variables_resolved: resolved,
    warnings,
    requires_approval: true,
  };
}

function isToday(iso: string | null | undefined): boolean {
  if (!iso) return false;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return false;
  const now = new Date();
  return d.toDateString() === now.toDateString();
}

export function buildWorkspaceSummary(
  items: OperatorQueueItem[],
  currentOperatorId?: string | null,
): OperatorWorkspaceSummary {
  let needs_attention_count = 0;
  let breached_sla_count = 0;
  let unassigned_count = 0;
  let assigned_to_me_count = 0;
  let high_priority_count = 0;
  let resolved_today_count = 0;

  for (const item of items) {
    if (item.status === 'needs_attention') needs_attention_count += 1;
    if (item.sla_state === 'breached') breached_sla_count += 1;
    if (item.status === 'unassigned') unassigned_count += 1;
    if (currentOperatorId && item.assigned_operator_id === currentOperatorId) {
      assigned_to_me_count += 1;
    }
    if (item.priority === 'urgent' || item.priority === 'high') high_priority_count += 1;
    if (item.status === 'resolved' && isToday(item.last_outbound_at)) {
      resolved_today_count += 1;
    }
  }

  return {
    needs_attention_count,
    breached_sla_count,
    unassigned_count,
    assigned_to_me_count,
    high_priority_count,
    resolved_today_count,
  };
}

/**
 * Derive per-operator workload rows from the current queue. Augment with
 * historical analytics (resolved today, avg response minutes) when provided.
 */
export function buildOperatorWorkload(
  items: OperatorQueueItem[],
  historical?: Array<{
    operator_id: string;
    operator_name?: string | null;
    resolved_today?: number | null;
    avg_response_minutes?: number | null;
  }> | null,
): OperatorWorkloadRow[] {
  const byOperator = new Map<string, OperatorWorkloadRow>();

  for (const item of items) {
    if (item.status === 'resolved') continue;
    const opId = item.assigned_operator_id ?? 'unassigned';
    const name = item.assigned_operator_name ?? (opId === 'unassigned' ? 'Unassigned' : opId.slice(0, 8));
    const existing = byOperator.get(opId) ?? {
      operator_id: opId,
      operator_name: name,
      assigned_count: 0,
      breached_sla_count: 0,
      high_priority_count: 0,
    };
    existing.assigned_count += 1;
    if (item.sla_state === 'breached') existing.breached_sla_count += 1;
    if (item.priority === 'urgent' || item.priority === 'high') {
      existing.high_priority_count = (existing.high_priority_count ?? 0) + 1;
    }
    byOperator.set(opId, existing);
  }

  if (historical) {
    for (const hist of historical) {
      const row = byOperator.get(hist.operator_id);
      if (row) {
        if (hist.resolved_today != null) row.resolved_today_count = hist.resolved_today;
        if (hist.avg_response_minutes != null) row.avg_response_minutes = hist.avg_response_minutes;
        if (hist.operator_name) row.operator_name = hist.operator_name;
      }
    }
  }

  return Array.from(byOperator.values()).sort((a, b) => {
    if (b.breached_sla_count !== a.breached_sla_count) return b.breached_sla_count - a.breached_sla_count;
    return b.assigned_count - a.assigned_count;
  });
}

/** Helper used by the conversation operator panel to derive SLA + waiting minutes. */
export function deriveConversationSla(
  conversation: ConversationDetail,
  traces: AgentDecisionTrace[] | null,
  rules?: OperatorSlaRule[] | null,
  now: Date = new Date(),
): { waitingMinutes: number | null; slaState: OperatorSlaState; priority: OperatorConversationPriority } {
  const lastInboundAt = conversation.last_message_at ?? null;
  const lastOutboundAt = conversation.last_operator_action_at ?? null;
  const waitingMinutes = calculateWaitingMinutes(lastInboundAt, lastOutboundAt, now);
  const trace = latestTraceForConversation(traces, conversation.id);
  const priority = inferOperatorPriority({
    handoff_required: conversation.handoff_required,
    risk_level: trace?.risk_score?.risk_level ?? null,
    waiting_minutes: waitingMinutes,
    unpaid_order:
      conversation.linked_order?.payment_status === 'unpaid' ||
      conversation.linked_order?.payment_status === 'pending',
    repeat_customer: conversation.customer_profile?.is_repeat_customer ?? null,
    priority_level: conversation.priority_level ?? null,
  });
  const slaState = calculateSlaState(waitingMinutes, priority, rules ?? null);
  return { waitingMinutes, slaState, priority };
}

export { toOperatorPriority };
