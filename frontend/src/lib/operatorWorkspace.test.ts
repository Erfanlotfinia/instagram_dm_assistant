import { describe, expect, it } from 'vitest';

import {
  buildCustomerTimeline,
  buildOperatorQueueItems,
  buildOperatorWorkload,
  buildWorkspaceSummary,
  calculateSlaState,
  calculateWaitingMinutes,
  deriveConversationSla,
  inferOperatorPriority,
  renderQuickReply,
} from './operatorWorkspace';
import type { Conversation, ConversationDetail } from '../types/conversation';
import type { QuickReplyTemplate } from '../types/sprint5Operator';

const NOW = new Date('2026-06-30T12:00:00Z');

function minutesAgo(mins: number): string {
  return new Date(NOW.getTime() - mins * 60_000).toISOString();
}

function baseConversation(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: 'c1',
    shop_id: 'shop-1',
    instagram_account_id: 'ig-1',
    customer_id: 'cust-1',
    state: 'open',
    workflow_state: 'idle',
    agent_paused: false,
    handoff_required: false,
    handoff_reason: null,
    last_message_at: null,
    last_intent: null,
    assigned_operator_id: null,
    created_at: minutesAgo(120),
    updated_at: minutesAgo(10),
    last_message_text: 'hi',
    last_message_direction: 'inbound',
    ...overrides,
  };
}

describe('calculateWaitingMinutes', () => {
  it('returns null when no inbound timestamp', () => {
    expect(calculateWaitingMinutes(null, null, NOW)).toBeNull();
  });

  it('returns 0 when outbound is newer than or equal to inbound', () => {
    expect(calculateWaitingMinutes(minutesAgo(10), minutesAgo(5), NOW)).toBe(0);
    expect(calculateWaitingMinutes(minutesAgo(10), minutesAgo(10), NOW)).toBe(0);
  });

  it('returns minutes since inbound when customer is waiting', () => {
    expect(calculateWaitingMinutes(minutesAgo(30), null, NOW)).toBe(30);
    expect(calculateWaitingMinutes(minutesAgo(30), minutesAgo(40), NOW)).toBe(30);
  });
});

describe('calculateSlaState', () => {
  it('returns unknown when waitingMinutes is null', () => {
    expect(calculateSlaState(null, 'normal')).toBe('unknown');
  });

  it('returns within_sla below 80% target', () => {
    expect(calculateSlaState(50, 'normal')).toBe('within_sla'); // target 120
    expect(calculateSlaState(10, 'urgent')).toBe('within_sla'); // target 15
  });

  it('returns approaching_breach at >=80% target', () => {
    expect(calculateSlaState(100, 'normal')).toBe('approaching_breach'); // 80% of 120 = 96
    expect(calculateSlaState(12, 'urgent')).toBe('approaching_breach'); // 80% of 15 = 12
  });

  it('returns breached at >= target', () => {
    expect(calculateSlaState(120, 'normal')).toBe('breached');
    expect(calculateSlaState(15, 'urgent')).toBe('breached');
  });

  it('honors custom rules when provided', () => {
    // 80% of 60 = 48; 50 >= 48 -> approaching_breach
    expect(
      calculateSlaState(50, 'normal', [
        { id: 'r1', label: 'Custom', target_minutes: 60, priority: 'normal', enabled: true },
      ]),
    ).toBe('approaching_breach');
    expect(
      calculateSlaState(70, 'normal', [
        { id: 'r1', label: 'Custom', target_minutes: 60, priority: 'normal', enabled: false },
      ]),
    ).toBe('within_sla'); // disabled rule ignored -> default 120
  });
});

describe('inferOperatorPriority', () => {
  it('returns urgent for critical risk with handoff', () => {
    expect(inferOperatorPriority({ handoff_required: true, risk_level: 'critical' })).toBe('urgent');
  });

  it('returns urgent for handoff waiting >= 30 minutes', () => {
    expect(inferOperatorPriority({ handoff_required: true, waiting_minutes: 30 })).toBe('urgent');
  });

  it('returns high for high risk', () => {
    expect(inferOperatorPriority({ risk_level: 'high' })).toBe('high');
  });

  it('returns high for high-value order', () => {
    expect(inferOperatorPriority({ high_value_order: true })).toBe('high');
  });

  it('returns high for handoff + unpaid order', () => {
    expect(inferOperatorPriority({ handoff_required: true, unpaid_order: true })).toBe('high');
  });

  it('returns high for revenue opportunity', () => {
    expect(inferOperatorPriority({ revenue_opportunity: true })).toBe('high');
  });

  it('returns normal by default', () => {
    expect(inferOperatorPriority({})).toBe('normal');
  });

  it('returns low when priority_level is low and no other signals', () => {
    expect(inferOperatorPriority({ priority_level: 'low' })).toBe('low');
  });
});

describe('buildOperatorQueueItems', () => {
  it('returns empty array when no conversations', () => {
    expect(buildOperatorQueueItems({ conversations: [], now: () => NOW })).toEqual([]);
  });

  it('dedupes by conversation id', () => {
    const c = baseConversation();
    const items = buildOperatorQueueItems({ conversations: [c, c], now: () => NOW });
    expect(items).toHaveLength(1);
  });

  it('sorts breached SLA first, then priority, then unassigned handoffs, then newest inbound', () => {
    const breached = baseConversation({
      id: 'breached',
      last_message_at: minutesAgo(200), // normal target 120 -> breached
      last_message_direction: 'inbound',
    });
    const urgent = baseConversation({
      id: 'urgent',
      last_message_at: minutesAgo(5),
      priority_level: 'urgent',
      last_message_direction: 'inbound',
    });
    const unassignedHandoff = baseConversation({
      id: 'unassigned-handoff',
      handoff_required: true,
      last_message_at: minutesAgo(2),
      last_message_direction: 'inbound',
    });
    const newest = baseConversation({
      id: 'newest',
      last_message_at: minutesAgo(1),
      last_message_direction: 'inbound',
    });

    const items = buildOperatorQueueItems({
      conversations: [newest, unassignedHandoff, urgent, breached],
      now: () => NOW,
    });

    expect(items.map((i) => i.conversation_id)).toEqual([
      'breached',
      'urgent',
      'unassigned-handoff',
      'newest',
    ]);
  });

  it('attaches ai summary from latest trace', () => {
    const c = baseConversation({ id: 'c-with-trace' });
    const items = buildOperatorQueueItems({
      conversations: [c],
      decisionTraces: [
        {
          id: 't1',
          conversation_id: 'c-with-trace',
          message_id: null,
          agent_run_id: null,
          intent: 'buy',
          extracted_slots: {},
          normalized_slots: {},
          product_candidates: [],
          selected_product_id: null,
          variant_resolution: {},
          inventory_result: {},
          risk_score: {},
          order_action: {},
          next_state: 'idle',
          outbound_message_id: null,
          auto_send_allowed: true,
          human_handoff_required: false,
          reasoning_summary: 'Customer wants a red shirt.',
          created_at: minutesAgo(5),
        },
      ],
      now: () => NOW,
    });
    expect(items[0].ai_summary).toBe('Customer wants a red shirt.');
  });

  it('attaches revenue context from linked order', () => {
    const c = baseConversation({
      id: 'c-with-order',
      linked_order: { id: 'order-12345678', status: 'paid', payment_status: 'paid', total_amount: '50' },
    });
    const items = buildOperatorQueueItems({ conversations: [c], now: () => NOW });
    expect(items[0].revenue_context).toContain('order-12');
    expect(items[0].revenue_context).toContain('paid');
  });
});

describe('buildCustomerTimeline', () => {
  it('merges messages, events, traces, orders and sorts newest first', () => {
    const items = buildCustomerTimeline({
      messages: [
        { id: 'm1', conversation_id: 'c1', direction: 'inbound', message_type: 'text', text: 'hello', created_at: minutesAgo(40) },
        { id: 'm2', conversation_id: 'c1', direction: 'outbound', message_type: 'text', text: 'hi back', created_at: minutesAgo(20) },
      ],
      events: [
        {
          id: 'e1',
          conversation_id: 'c1',
          event_type: 'handoff_required',
          title: 'Handoff required',
          description: null,
          metadata: null,
          created_by_user_id: null,
          created_at: minutesAgo(15),
        },
      ],
      decisionTraces: [
        {
          id: 't1',
          conversation_id: 'c1',
          message_id: null,
          agent_run_id: null,
          intent: 'buy',
          extracted_slots: {},
          normalized_slots: {},
          product_candidates: [],
          selected_product_id: null,
          variant_resolution: {},
          inventory_result: {},
          risk_score: {},
          order_action: {},
          next_state: 'idle',
          outbound_message_id: null,
          auto_send_allowed: true,
          human_handoff_required: false,
          reasoning_summary: 'intent buy',
          created_at: minutesAgo(30),
        },
      ],
      orders: [
        {
          id: 'order-abc',
          shop_id: 'shop-1',
          customer_id: 'cust-1',
          conversation_id: 'c1',
          status: 'paid',
          subtotal_amount: '50',
          shipping_amount: '5',
          discount_amount: '0',
          total_amount: '55',
          currency: 'USD',
          payment_status: 'paid',
          shipping_status: 'not_started',
          customer_name: 'Jane',
          phone: '',
          city: '',
          address: '',
          postal_code: '',
          notes: null,
          created_at: minutesAgo(10),
          items: [],
          payments: [],
          shipments: [],
          timeline: [],
        },
      ],
      conversationId: 'c1',
      shopId: 'shop-1',
    });

    expect(items.length).toBe(5);
    // newest first
    const times = items.map((i) => (i.created_at ? new Date(i.created_at).getTime() : 0));
    expect(times).toEqual([...times].sort((a, b) => b - a));
    expect(items[0].type).toBe('order');
    expect(items.find((i) => i.type === 'handoff')).toBeTruthy();
    expect(items.find((i) => i.type === 'ai_decision')).toBeTruthy();
  });

  it('returns empty array when no data', () => {
    expect(buildCustomerTimeline({})).toEqual([]);
  });
});

describe('renderQuickReply', () => {
  const template: QuickReplyTemplate = {
    id: 'greeting',
    title: 'Greeting',
    category: 'greeting',
    body: 'Hi {{customer_name}}, thanks for reaching out about {{product_name}}!',
    variables: ['customer_name', 'product_name'],
    enabled: true,
  };

  it('substitutes provided variables', () => {
    const draft = renderQuickReply(template, { customer_name: 'Jane', product_name: 'Red Shirt' }, 'c1');
    expect(draft.body).toBe('Hi Jane, thanks for reaching out about Red Shirt!');
    expect(draft.warnings).toEqual([]);
    expect(draft.requires_approval).toBe(true);
    expect(draft.source).toBe('quick_reply');
    expect(draft.conversation_id).toBe('c1');
  });

  it('leaves unresolved variables visible and warns', () => {
    const draft = renderQuickReply(template, { customer_name: 'Jane' }, 'c1');
    expect(draft.body).toBe('Hi Jane, thanks for reaching out about {{product_name}}!');
    expect(draft.warnings).toEqual(['Unresolved variable: product_name']);
  });
});

describe('buildWorkspaceSummary', () => {
  it('counts each KPI correctly', () => {
    const items = buildOperatorQueueItems({
      conversations: [
        baseConversation({ id: 'att', needs_attention: true }),
        baseConversation({ id: 'breach', last_message_at: minutesAgo(200), last_message_direction: 'inbound' }),
        baseConversation({ id: 'un', handoff_required: true }),
        baseConversation({ id: 'mine', assigned_operator_id: 'op-me' }),
        baseConversation({ id: 'high', priority_level: 'urgent' }),
      ],
      currentOperatorId: 'op-me',
      now: () => NOW,
    });
    const summary = buildWorkspaceSummary(items, 'op-me');
    expect(summary.needs_attention_count).toBe(1);
    expect(summary.breached_sla_count).toBe(1);
    expect(summary.unassigned_count).toBe(1);
    expect(summary.assigned_to_me_count).toBe(1);
    expect(summary.high_priority_count).toBeGreaterThanOrEqual(1);
  });
});

describe('buildOperatorWorkload', () => {
  it('groups by assigned operator and counts SLA + priority', () => {
    const items = buildOperatorQueueItems({
      conversations: [
        baseConversation({ id: 'a', assigned_operator_id: 'op-1', assigned_operator: { id: 'op-1', full_name: 'Ada' }, last_message_at: minutesAgo(200), last_message_direction: 'inbound' }),
        baseConversation({ id: 'b', assigned_operator_id: 'op-1', assigned_operator: { id: 'op-1', full_name: 'Ada' }, last_message_at: minutesAgo(5), last_message_direction: 'inbound', priority_level: 'urgent' }),
        baseConversation({ id: 'c', assigned_operator_id: 'op-2', assigned_operator: { id: 'op-2', full_name: 'Bo' }, last_message_at: minutesAgo(5), last_message_direction: 'inbound' }),
      ],
      now: () => NOW,
    });
    const rows = buildOperatorWorkload(items);
    const ada = rows.find((r) => r.operator_id === 'op-1');
    expect(ada?.assigned_count).toBe(2);
    expect(ada?.breached_sla_count).toBe(1);
    // Both 'a' (waiting 200m -> high) and 'b' (urgent) infer as high priority.
    expect(ada?.high_priority_count).toBe(2);
    expect(rows.find((r) => r.operator_id === 'op-2')?.assigned_count).toBe(1);
  });
});

describe('deriveConversationSla', () => {
  it('returns waiting minutes, sla state, and priority for a detail object', () => {
    const detail: ConversationDetail = {
      ...baseConversation({ id: 'c-detail', last_message_at: minutesAgo(140), last_message_direction: 'inbound' }),
      messages: [],
      slots: null,
      agent_runs: [],
      agent_actions: [],
    };
    const result = deriveConversationSla(detail, null, null, NOW);
    expect(result.waitingMinutes).toBe(140);
    expect(result.slaState).toBe('breached');
    expect(result.priority).toBe('high'); // handoff_required false, waiting >=60 -> high
  });
});
