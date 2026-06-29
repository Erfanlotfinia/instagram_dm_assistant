import { describe, expect, it } from 'vitest';

import {
  buildLostDemandInsights,
  buildPostRevenueInsights,
  buildRecoveryMessageDraft,
  buildRecoveryOpportunities,
  buildRestockWaitlist,
  buildRevenueRecoveryDashboard,
  severityFromValue,
} from './revenueRecovery';
import type { RevenueRecoveryAggregationInput } from '../types/sprint4Revenue';
import type { LostDemandRow, UnavailableDemandRow } from '../types/competitive';
import type { PostRevenueRow } from '../types/sprintD';
import type { Order } from '../types/order';
import type { Conversation } from '../types/conversation';
import type { Product } from '../types/product';

function product(overrides: Partial<Product> = {}): Product {
  return {
    id: 'p1',
    shop_id: 's1',
    title: 'Oversized Tee',
    description: null,
    status: 'active',
    base_price: '500000',
    currency: 'IRR',
    main_image_url: null,
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
    ...overrides,
  };
}

function order(overrides: Partial<Order> = {}): Order {
  return {
    id: 'o1',
    shop_id: 's1',
    customer_id: 'c1',
    conversation_id: 'conv1',
    status: 'payment_pending',
    subtotal_amount: '500000',
    shipping_amount: '0',
    discount_amount: '0',
    total_amount: '500000',
    currency: 'IRR',
    payment_status: 'unpaid',
    shipping_status: 'not_started',
    customer_name: 'Customer',
    phone: '',
    city: '',
    address: '',
    postal_code: '',
    notes: null,
    expires_at: null,
    created_at: '2026-06-29T00:00:00Z',
    updated_at: '2026-06-29T00:00:00Z',
    items: [],
    payments: [],
    shipments: [],
    timeline: [],
    ...overrides,
  };
}

function unavailableRow(overrides: Partial<UnavailableDemandRow> = {}): UnavailableDemandRow {
  return {
    requested_color: null,
    requested_size: null,
    product_id: 'p1',
    count: 1,
    lost_revenue_estimate: '0',
    ...overrides,
  };
}

function lostRow(overrides: Partial<LostDemandRow> = {}): LostDemandRow {
  return {
    requested_product: 'Oversized Tee',
    requested_color: null,
    requested_size: null,
    product_id: 'p1',
    count: 1,
    estimated_lost_revenue: '0',
    reason: 'out_of_stock',
    ...overrides,
  };
}

function postRevenue(overrides: Partial<PostRevenueRow> = {}): PostRevenueRow {
  return {
    instagram_post_url: 'https://instagram.com/p/abc',
    product_id: 'p1',
    conversations: 10,
    draft_orders: 2,
    paid_orders: 1,
    revenue: '500000',
    conversion_rate: 0.1,
    abandoned_rate: 0.8,
    ...overrides,
  };
}

function conversation(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: 'conv1',
    shop_id: 's1',
    instagram_account_id: 'ig1',
    customer_id: 'c1',
    state: 'open',
    workflow_state: 'waiting_for_payment',
    agent_paused: false,
    last_intent: 'buy',
    assigned_operator_id: null,
    linked_order: null,
    ...overrides,
  } as Conversation;
}

function input(overrides: Partial<RevenueRecoveryAggregationInput> = {}): RevenueRecoveryAggregationInput {
  return { shopId: 's1', products: [product()], ...overrides };
}

describe('severityFromValue', () => {
  it('returns high for large value or count', () => {
    expect(severityFromValue(1_500_000, 0)).toBe('high');
    expect(severityFromValue(null, 12)).toBe('high');
  });
  it('returns medium for moderate signals', () => {
    expect(severityFromValue(250_000, 0)).toBe('medium');
    expect(severityFromValue(null, 3)).toBe('medium');
  });
  it('returns low otherwise and never throws on null', () => {
    expect(severityFromValue(null, null)).toBe('low');
    expect(severityFromValue(undefined as never, undefined as never)).toBe('low');
  });
});

describe('buildRecoveryOpportunities', () => {
  it('creates an abandoned_order opportunity', () => {
    const ops = buildRecoveryOpportunities(
      input({ orders: [order({ status: 'expired', payment_status: 'unpaid' })] }),
    );
    expect(ops.some((o) => o.type === 'abandoned_order')).toBe(true);
  });

  it('creates an unpaid_order opportunity', () => {
    const ops = buildRecoveryOpportunities(input({ orders: [order({ status: 'payment_pending' })] }));
    expect(ops.some((o) => o.type === 'unpaid_order')).toBe(true);
  });

  it('creates an unavailable_product opportunity when no variant', () => {
    const ops = buildRecoveryOpportunities(
      input({ unavailableDemand: [unavailableRow({ requested_color: null, requested_size: null })] }),
    );
    expect(ops.some((o) => o.type === 'unavailable_product')).toBe(true);
  });

  it('creates an unavailable_variant opportunity when color/size present', () => {
    const ops = buildRecoveryOpportunities(
      input({ unavailableDemand: [unavailableRow({ requested_color: 'red', requested_size: 'L' })] }),
    );
    expect(ops.some((o) => o.type === 'unavailable_variant')).toBe(true);
  });

  it('upgrades repeated demand to restock_waitlist', () => {
    const ops = buildRecoveryOpportunities(
      input({
        unavailableDemand: [
          unavailableRow({ count: 4, requested_color: 'red' }),
        ],
      }),
    );
    expect(ops.some((o) => o.type === 'restock_waitlist')).toBe(true);
  });

  it('creates high_intent_no_order for waiting conversations without paid order', () => {
    const ops = buildRecoveryOpportunities(input({ conversations: [conversation()] }));
    expect(ops.some((o) => o.type === 'high_intent_no_order')).toBe(true);
  });

  it('skips high_intent when linked order is paid', () => {
    const ops = buildRecoveryOpportunities(
      input({
        conversations: [
          conversation({
            linked_order: { id: 'o9', status: 'paid', payment_status: 'paid', total_amount: '100' },
          }),
        ],
      }),
    );
    expect(ops.some((o) => o.type === 'high_intent_no_order')).toBe(false);
  });

  it('deduplicates opportunities by composite key', () => {
    const ops = buildRecoveryOpportunities(
      input({
        unavailableDemand: [
          unavailableRow({ product_id: 'p1', requested_color: 'red', count: 1 }),
          unavailableRow({ product_id: 'p1', requested_color: 'red', count: 1 }),
        ],
      }),
    );
    const variantOps = ops.filter((o) => o.type === 'unavailable_variant');
    expect(variantOps.length).toBe(1);
  });

  it('returns empty array for empty input without throwing', () => {
    expect(buildRecoveryOpportunities(input())).toEqual([]);
    expect(buildRecoveryOpportunities({ shopId: 's1' })).toEqual([]);
  });
});

describe('buildLostDemandInsights', () => {
  it('groups lost demand by product/variant and sums counts', () => {
    const insights = buildLostDemandInsights(
      input({
        lostDemand: [
          lostRow({ count: 2, requested_color: 'red' }),
          lostRow({ count: 3, requested_color: 'red' }),
          lostRow({ count: 1, requested_color: 'blue' }),
        ],
      }),
    );
    const red = insights.find((i) => i.variant_label === 'red');
    expect(red?.demand_count).toBe(5);
    const blue = insights.find((i) => i.variant_label === 'blue');
    expect(blue?.demand_count).toBe(1);
  });

  it('marks value unavailable when no estimated revenue present', () => {
    const insights = buildLostDemandInsights(
      input({ lostDemand: [lostRow({ estimated_lost_revenue: '0', count: 1 })] }),
    );
    expect(insights[0].estimated_lost_value).toBe(0);
  });

  it('never throws on missing input', () => {
    expect(buildLostDemandInsights(input())).toEqual([]);
  });
});

describe('buildRestockWaitlist', () => {
  it('derives waitlist rows only when customer/conversation is known', () => {
    const items = buildRestockWaitlist(
      input({
        unavailableDemandLogs: [
          { id: 'l1', product_id: 'p1', requested_quantity: 1, reason: 'out_of_stock', conversation_id: 'conv1', customer_id: 'c1' },
          { id: 'l2', product_id: 'p1', requested_quantity: 1, reason: 'out_of_stock' },
        ],
      }),
    );
    expect(items.length).toBe(1);
    expect(items[0].conversation_id).toBe('conv1');
    expect(items[0].suggested_message).toMatch(/available again/i);
    expect(items[0].status).toBe('waiting');
  });

  it('returns empty array when no logs have customer/conversation', () => {
    expect(buildRestockWaitlist(input())).toEqual([]);
  });
});

describe('buildRecoveryMessageDraft', () => {
  it('produces a professional preview-only draft for unpaid orders', () => {
    const ops = buildRecoveryOpportunities(input({ orders: [order()] }));
    const draft = buildRecoveryMessageDraft(ops[0]);
    expect(draft.requires_human_approval).toBe(true);
    expect(draft.tone).toBe('professional');
    expect(draft.message.length).toBeGreaterThan(0);
    expect(draft.opportunity_id).toBe(ops[0].id);
  });

  it('uses friendly tone for restock waitlist', () => {
    const ops = buildRecoveryOpportunities(
      input({ unavailableDemand: [unavailableRow({ count: 4, requested_color: 'red' })] }),
    );
    const waitlist = ops.find((o) => o.type === 'restock_waitlist')!;
    const draft = buildRecoveryMessageDraft(waitlist);
    expect(draft.tone).toBe('friendly');
  });
});

describe('buildPostRevenueInsights', () => {
  it('flags high-demand low-conversion posts', () => {
    const insights = buildPostRevenueInsights(
      input({
        postRevenue: [postRevenue({ conversations: 10, paid_orders: 1, conversion_rate: 0.1 })],
      }),
    );
    expect(insights[0].insight).toMatch(/low conversion/i);
  });

  it('flags high revenue posts', () => {
    const insights = buildPostRevenueInsights(
      input({
        postRevenue: [postRevenue({ conversations: 10, paid_orders: 8, conversion_rate: 0.8, revenue: '4000000' })],
      }),
    );
    expect(insights[0].insight).toMatch(/high revenue/i);
  });

  it('flags high lost demand posts', () => {
    const insights = buildPostRevenueInsights(
      input({
        postPerformance: [
          { instagram_post_url: 'https://instagram.com/p/x', product_id: 'p1', inbound_messages: 20, draft_orders: 0, paid_orders: 0, revenue: '0', conversion_rate: 0 },
        ],
      }),
    );
    expect(insights.some((i) => /lost demand/i.test(i.insight))).toBe(true);
  });

  it('never throws on empty input', () => {
    expect(buildPostRevenueInsights(input())).toEqual([]);
  });
});

describe('buildRevenueRecoveryDashboard', () => {
  it('composes opportunities, lost demand, waitlist, post insights and totals', () => {
    const dashboard = buildRevenueRecoveryDashboard(
      input({
        orders: [order({ status: 'expired', payment_status: 'unpaid', total_amount: '1500000' })],
        lostDemand: [lostRow({ count: 12, estimated_lost_revenue: '1500000' })],
        postRevenue: [postRevenue()],
        unavailableDemandLogs: [
          { id: 'l1', product_id: 'p1', requested_quantity: 1, reason: 'out_of_stock', conversation_id: 'conv1' },
        ],
      }),
    );
    expect(dashboard.opportunities.length).toBeGreaterThan(0);
    expect(dashboard.lostDemand.length).toBeGreaterThan(0);
    expect(dashboard.restockWaitlist.length).toBeGreaterThan(0);
    expect(dashboard.postInsights.length).toBeGreaterThan(0);
    expect(dashboard.highPriorityCount).toBeGreaterThanOrEqual(0);
    expect(dashboard.totalEstimatedRecoverableValue).not.toBe(null);
  });

  it('returns null total when no opportunity has a value', () => {
    const dashboard = buildRevenueRecoveryDashboard(
      input({ conversations: [conversation()] }),
    );
    expect(dashboard.totalEstimatedRecoverableValue).toBe(null);
  });
});
