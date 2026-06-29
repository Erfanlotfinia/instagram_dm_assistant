import type {
  LostDemandInsight,
  PostRevenueInsight,
  RecoveryMessageDraft,
  RecoveryMessageTone,
  RestockWaitlistItem,
  RevenueRecoveryAggregationInput,
  RevenueRecoveryDashboard,
  RevenueRecoveryOpportunity,
  RevenueRecoveryOpportunityType,
  RevenueRecoverySeverity,
} from '../types/sprint4Revenue';
import type { LostDemandRow, PostPerformanceRow, UnavailableDemandRow } from '../types/competitive';
import type { PostRevenueRow } from '../types/sprintD';
import type { Order } from '../types/order';
import type { Conversation } from '../types/conversation';
import type { Product } from '../types/product';

/**
 * Sprint 4 — Revenue Recovery
 *
 * Deterministic, pure revenue-recovery builders. No LLM, no React, no I/O.
 * Aggregates existing analytics / order / conversation / catalog rows into
 * prioritized recovery opportunities, lost-demand insights, restock waitlist,
 * post-to-revenue insights, and preview-only recovery message drafts.
 *
 * Every builder is null-safe: missing or partial input never throws; it just
 * yields a partial result. Money fields are strings in the backend contract
 * and are parsed with `parseMoney`.
 */

/* ─── Constants ─── */

/** Repeated unavailable demand for the same product at/above this count becomes a waitlist / spike signal. */
const RESTOCK_WAITLIST_THRESHOLD = 3;
/** Demand count at/above which a lost-demand insight is "high" severity regardless of value. */
const HIGH_DEMAND_COUNT = 10;
const MEDIUM_DEMAND_COUNT = 3;
/** Estimated value (in shop currency minor units treated as raw number) thresholds for severity. */
const HIGH_VALUE_THRESHOLD = 1_000_000;
const MEDIUM_VALUE_THRESHOLD = 200_000;
/** Post insight thresholds. */
const LOW_CONVERSION_THRESHOLD = 0.2;
const LOW_CONVERSION_MIN_CONVERSATIONS = 5;
const HIGH_LOST_DEMAND_THRESHOLD = 5;

/* ─── Private helpers ─── */

function parseMoney(value: string | number | null | undefined): number | null {
  if (value == null) return null;
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function severityFromValueInternal(value: number | null, count: number | null): RevenueRecoverySeverity {
  const v = value ?? null;
  const c = count ?? 0;
  if ((v != null && v >= HIGH_VALUE_THRESHOLD) || c >= HIGH_DEMAND_COUNT) return 'high';
  if ((v != null && v >= MEDIUM_VALUE_THRESHOLD) || c >= MEDIUM_DEMAND_COUNT) return 'medium';
  return 'low';
}

function dedupKey(op: RevenueRecoveryOpportunity): string {
  const identity =
    op.order_id ??
    op.conversation_id ??
    op.product_id ??
    op.post_url ??
    op.id;
  return `${op.type}:${identity}`;
}

function keepHigherSeverity(a: RevenueRecoverySeverity, b: RevenueRecoverySeverity): RevenueRecoverySeverity {
  const order: Record<RevenueRecoverySeverity, number> = { high: 3, medium: 2, low: 1 };
  return order[a] >= order[b] ? a : b;
}

function productName(products: Product[] | null | undefined, productId?: string | null): string | undefined {
  if (!productId || !products) return undefined;
  return products.find((p) => p.id === productId)?.title;
}

function variantLabel(color?: string | null, size?: string | null): string | null {
  const parts = [color, size].filter((p): p is string => Boolean(p));
  return parts.length > 0 ? parts.join(' · ') : null;
}

function orderTotal(order: Order): number | null {
  return parseMoney(order.total_amount);
}

/** Abandoned = expired or cancelled without being paid. */
function isAbandonedOrder(order: Order): boolean {
  const terminal = order.status === 'expired' || order.status === 'cancelled';
  const notPaid = order.payment_status !== 'paid';
  return terminal && notPaid;
}

/** Unpaid = payment_pending or unpaid on a non-terminal order. */
function isUnpaidOrder(order: Order): boolean {
  if (order.status === 'paid') return false;
  return order.payment_status === 'unpaid' || order.payment_status === 'pending' || order.status === 'payment_pending';
}

/* ─── 1. severityFromValue ─── */

/**
 * Map an estimated value and/or demand count to a recovery severity.
 * Never throws on missing values. Pure function — no I/O.
 */
export function severityFromValue(value: number | null, count: number | null): RevenueRecoverySeverity {
  return severityFromValueInternal(value, count);
}

/* ─── 2. buildRecoveryOpportunities ─── */

function opportunityFromOrder(
  order: Order,
  shopId: string,
  type: RevenueRecoveryOpportunityType,
  products: Product[] | null | undefined,
): RevenueRecoveryOpportunity {
  const value = orderTotal(order);
  const severity = severityFromValue(value, null);
  const firstItem = order.items[0];
  const productTitle = firstItem
    ? firstItem.product_title_snapshot || productName(products, firstItem.product_id ?? undefined)
    : undefined;
  const title =
    type === 'abandoned_order'
      ? `Abandoned order ${order.id.slice(0, 8)}${productTitle ? ` — ${productTitle}` : ''}`
      : `Unpaid order ${order.id.slice(0, 8)}${productTitle ? ` — ${productTitle}` : ''}`;
  const reason =
    type === 'abandoned_order'
      ? `Order ${order.id} expired or was cancelled without payment${value != null ? ` (≈ ${value.toLocaleString()})` : ''}.`
      : `Order ${order.id} is awaiting payment${value != null ? ` (≈ ${value.toLocaleString()})` : ''}.`;
  return {
    id: `${type}:${order.id}`,
    type,
    severity,
    shop_id: shopId,
    customer_id: order.customer_id,
    conversation_id: order.conversation_id,
    order_id: order.id,
    product_id: firstItem?.product_id ?? null,
    variant_id: firstItem?.product_variant_id ?? null,
    title,
    reason,
    estimated_value: value,
    suggested_action:
      type === 'abandoned_order'
        ? 'Send a payment reminder or re-engage the customer.'
        : 'Resend the payment link and follow up.',
    action_to: `/orders/${order.id}`,
    created_at: order.created_at,
    source: 'order',
  };
}

function opportunityFromUnavailable(
  row: UnavailableDemandRow,
  shopId: string,
  products: Product[] | null | undefined,
  spikeCount?: number,
): RevenueRecoveryOpportunity {
  const hasVariant = Boolean(row.requested_color || row.requested_size);
  const type: RevenueRecoveryOpportunityType = hasVariant ? 'unavailable_variant' : 'unavailable_product';
  const value = parseMoney(row.lost_revenue_estimate);
  const count = row.count;
  const severity = severityFromValue(value, count);
  const title = productName(products, row.product_id) ?? row.requested_color ?? row.requested_size ?? 'Unknown product';
  const variant = variantLabel(row.requested_color, row.requested_size);
  return {
    id: `${type}:${row.product_id ?? 'unknown'}:${variant ?? 'none'}`,
    type: spikeCount && spikeCount >= RESTOCK_WAITLIST_THRESHOLD ? 'restock_waitlist' : type,
    severity,
    shop_id: shopId,
    product_id: row.product_id,
    variant_id: null,
    title: variant ? `${title} — ${variant}` : title,
    reason: `Requested ${count}× unavailable ${hasVariant ? 'variant' : 'product'}${value != null ? ` (≈ ${value.toLocaleString()} lost)` : ''}.`,
    estimated_value: value,
    suggested_action:
      spikeCount && spikeCount >= RESTOCK_WAITLIST_THRESHOLD
        ? 'Restock and notify waiting customers.'
        : 'Restock or add a fulfillable variant / alias.',
    action_to: row.product_id ? `/catalog/products/${row.product_id}` : '/analytics/demand',
    source: 'analytics',
  };
}

function opportunityFromConversation(
  conversation: Conversation,
  shopId: string,
  products: Product[] | null | undefined,
): RevenueRecoveryOpportunity | null {
  // High-intent = waiting for payment or confirmation with no paid linked order.
  const isWaiting =
    conversation.workflow_state === 'waiting_for_payment' ||
    conversation.workflow_state === 'waiting_for_confirmation';
  if (!isWaiting) return null;
  const linked = conversation.linked_order;
  if (linked && linked.payment_status === 'paid') return null;

  const productTitle = conversation.linked_product?.title;
  const product = productTitle
    ? undefined
    : productName(products, undefined);
  const title = `High-intent conversation — ${conversation.last_intent ?? 'ready to order'}`;
  return {
    id: `high_intent_no_order:${conversation.id}`,
    type: 'high_intent_no_order',
    severity: 'medium',
    shop_id: shopId,
    customer_id: conversation.customer_id,
    conversation_id: conversation.id,
    product_id: conversation.linked_product?.id ?? null,
    title: productTitle ? `${title} — ${productTitle}` : title,
    reason: `Conversation ${conversation.id} is in ${conversation.workflow_state} without a paid order.`,
    estimated_value: linked ? parseMoney(linked.total_amount) : null,
    suggested_action: 'Follow up with the customer to complete the order.',
    action_to: `/inbox/${conversation.id}`,
    source: 'conversation',
  };
}

function opportunityFromPostSpike(
  postUrl: string,
  demandCount: number,
  shopId: string,
): RevenueRecoveryOpportunity {
  return {
    id: `post_demand_spike:${postUrl}`,
    type: 'post_demand_spike',
    severity: severityFromValue(null, demandCount),
    shop_id: shopId,
    post_url: postUrl,
    title: `Demand spike on post`,
    reason: `Post ${postUrl} generated ${demandCount} unfulfillable requests.`,
    estimated_value: null,
    suggested_action: 'Review stock for the linked product and consider a restock campaign.',
    action_to: '/analytics/revenue',
    source: 'analytics',
  };
}

/**
 * Build the prioritized, deduplicated opportunity list from the aggregation input.
 * Pure function — no I/O.
 */
export function buildRecoveryOpportunities(input: RevenueRecoveryAggregationInput): RevenueRecoveryOpportunity[] {
  const { shopId, products } = input;
  const byKey = new Map<string, RevenueRecoveryOpportunity>();

  const upsert = (op: RevenueRecoveryOpportunity) => {
    const key = dedupKey(op);
    const existing = byKey.get(key);
    if (!existing) {
      byKey.set(key, op);
      return;
    }
    const merged: RevenueRecoveryOpportunity = {
      ...existing,
      severity: keepHigherSeverity(existing.severity, op.severity),
      estimated_value: existing.estimated_value ?? op.estimated_value,
    };
    byKey.set(key, merged);
  };

  // Orders → abandoned / unpaid
  for (const order of input.orders ?? []) {
    if (isAbandonedOrder(order)) upsert(opportunityFromOrder(order, shopId, 'abandoned_order', products));
    else if (isUnpaidOrder(order)) upsert(opportunityFromOrder(order, shopId, 'unpaid_order', products));
  }

  // Unavailable demand → unavailable product/variant (+ restock_waitlist when repeated)
  const demandByProduct = new Map<string, number>();
  for (const row of input.unavailableDemand ?? []) {
    const pid = row.product_id ?? 'unknown';
    demandByProduct.set(pid, (demandByProduct.get(pid) ?? 0) + (row.count ?? 0));
  }
  for (const row of input.unavailableDemand ?? []) {
    const pid = row.product_id ?? 'unknown';
    upsert(opportunityFromUnavailable(row, shopId, products, demandByProduct.get(pid)));
  }

  // Conversations → high_intent_no_order
  for (const conversation of input.conversations ?? []) {
    const op = opportunityFromConversation(conversation, shopId, products);
    if (op) upsert(op);
  }

  // Post demand spikes from post performance when inbound is high relative to paid
  for (const post of input.postPerformance ?? []) {
    const demand = (post.inbound_messages ?? 0) - (post.paid_orders ?? 0);
    if (demand >= RESTOCK_WAITLIST_THRESHOLD && (post.paid_orders ?? 0) === 0) {
      upsert(opportunityFromPostSpike(post.instagram_post_url, demand, shopId));
    }
  }

  return Array.from(byKey.values()).sort((a, b) => {
    const order: Record<RevenueRecoverySeverity, number> = { high: 3, medium: 2, low: 1 };
    if (order[b.severity] !== order[a.severity]) return order[b.severity] - order[a.severity];
    return (b.estimated_value ?? 0) - (a.estimated_value ?? 0);
  });
}

/* ─── 3. buildLostDemandInsights ─── */

/**
 * Group lost/unavailable demand by product/variant, sum counts and estimated
 * lost value, and sort by severity then demand_count. Pure function — no I/O.
 */
export function buildLostDemandInsights(input: RevenueRecoveryAggregationInput): LostDemandInsight[] {
  const { products, lostDemand, unavailableDemand } = input;
  type Acc = {
    product_id?: string | null;
    product_name?: string | null;
    variant_label?: string | null;
    demand_count: number;
    lost_reason: string;
    estimated_lost_value: number | null;
    hasValue: boolean;
  };
  const groups = new Map<string, Acc>();

  const keyFor = (productId?: string | null, variantLabel?: string | null) =>
    `${productId ?? 'unknown'}::${variantLabel ?? 'none'}`;

  const accumulate = (row: {
    product_id?: string | null;
    requested_color?: string | null;
    requested_size?: string | null;
    count: number;
    reason?: string | null;
    estimated?: number | null;
  }) => {
    const variant = variantLabel(row.requested_color, row.requested_size);
    const key = keyFor(row.product_id, variant);
    const existing = groups.get(key) ?? {
      product_id: row.product_id ?? null,
      product_name: productName(products, row.product_id) ?? null,
      variant_label: variant,
      demand_count: 0,
      lost_reason: row.reason ?? 'Unavailable variant',
      estimated_lost_value: null as number | null,
      hasValue: false,
    };
    existing.demand_count += row.count ?? 0;
    if (row.reason) existing.lost_reason = row.reason;
    if (row.estimated != null) {
      existing.estimated_lost_value = (existing.estimated_lost_value ?? 0) + row.estimated;
      existing.hasValue = true;
    }
    groups.set(key, existing);
  };

  for (const row of lostDemand ?? []) {
    accumulate({
      product_id: row.product_id,
      requested_color: row.requested_color,
      requested_size: row.requested_size,
      count: row.count,
      reason: row.reason,
      estimated: parseMoney(row.estimated_lost_revenue),
    });
  }
  for (const row of unavailableDemand ?? []) {
    accumulate({
      product_id: row.product_id,
      requested_color: row.requested_color,
      requested_size: row.requested_size,
      count: row.count,
      reason: 'Unavailable variant',
      estimated: parseMoney(row.lost_revenue_estimate),
    });
  }

  return Array.from(groups.values())
    .map((acc) => {
      const severity = severityFromValue(acc.hasValue ? acc.estimated_lost_value : null, acc.demand_count);
      const insight: LostDemandInsight = {
        product_id: acc.product_id,
        product_name: acc.product_name,
        variant_label: acc.variant_label,
        demand_count: acc.demand_count,
        lost_reason: acc.hasValue ? acc.lost_reason : `${acc.lost_reason} (value unavailable)`,
        estimated_lost_value: acc.hasValue ? acc.estimated_lost_value : null,
        severity,
        action_to: acc.product_id ? `/catalog/products/${acc.product_id}` : '/analytics/demand',
      };
      return insight;
    })
    .sort((a, b) => {
      const order: Record<RevenueRecoverySeverity, number> = { high: 3, medium: 2, low: 1 };
      if (order[b.severity] !== order[a.severity]) return order[b.severity] - order[a.severity];
      return b.demand_count - a.demand_count;
    });
}

/* ─── 4. buildRestockWaitlist ─── */

const RESTOCK_MESSAGE =
  'Hi, the item you asked about is available again. Would you like me to reserve it for you?';

/**
 * Derive restock waitlist rows from raw unavailable demand logs where a
 * customer or conversation is known. Suggested messages are deterministic
 * and preview-only — never sent automatically. Pure function — no I/O.
 */
export function buildRestockWaitlist(input: RevenueRecoveryAggregationInput): RestockWaitlistItem[] {
  const { unavailableDemandLogs, products } = input;
  const items: RestockWaitlistItem[] = [];
  for (const log of unavailableDemandLogs ?? []) {
    if (!log.conversation_id && !log.customer_id) continue;
    const productTitle = productName(products, log.product_id) ?? log.product_id ?? 'Unknown product';
    const variant = variantLabel(
      log.requested_color_normalized ?? log.requested_color_raw,
      log.requested_size_normalized ?? log.requested_size_raw,
    );
    items.push({
      id: `waitlist:${log.id}`,
      customer_id: log.customer_id ?? null,
      conversation_id: log.conversation_id ?? null,
      product_id: log.product_id ?? null,
      variant_id: null,
      product_label: productTitle,
      requested_variant_label: variant,
      requested_at: log.requested_at ?? null,
      status: 'waiting',
      suggested_message: RESTOCK_MESSAGE,
    });
  }
  return items;
}

/* ─── 5. buildRecoveryMessageDraft ─── */

const DRAFT_TEMPLATES: Record<RevenueRecoveryOpportunityType, { message: string; tone: RecoveryMessageTone }> = {
  abandoned_order: {
    message:
      'Hi, we noticed you didn\'t finish your order. Your cart is still saved — would you like me to resend the payment link?',
    tone: 'professional',
  },
  unpaid_order: {
    message:
      'Hi, your order is still waiting for payment. I can resend the payment link whenever you\'re ready.',
    tone: 'professional',
  },
  unavailable_product: {
    message:
      'Hi, the product you asked about is back in stock. Would you like me to set up an order for you?',
    tone: 'professional',
  },
  unavailable_variant: {
    message:
      'Hi, the variant you wanted is available again. Would you like me to reserve it for you?',
    tone: 'professional',
  },
  restock_waitlist: {
    message: RESTOCK_MESSAGE,
    tone: 'friendly',
  },
  high_intent_no_order: {
    message:
      'Hi, I wanted to follow up on your interest — would you like me to help you place the order now?',
    tone: 'professional',
  },
  post_demand_spike: {
    message:
      'Internal note: this post is generating demand we can\'t fulfill. Review stock and consider a restock campaign.',
    tone: 'urgent',
  },
};

/**
 * Build a deterministic, preview-only recovery message draft for a single
 * opportunity. No LLM. `requires_human_approval` is always true — drafts are
 * never sent automatically by this sprint. Pure function — no I/O.
 */
export function buildRecoveryMessageDraft(
  opportunity: RevenueRecoveryOpportunity,
  overrides?: { customer_label?: string | null; channel_provider?: string | null },
): RecoveryMessageDraft {
  const template = DRAFT_TEMPLATES[opportunity.type] ?? DRAFT_TEMPLATES.high_intent_no_order;
  return {
    opportunity_id: opportunity.id,
    channel_provider: overrides?.channel_provider ?? null,
    conversation_id: opportunity.conversation_id ?? null,
    customer_label: overrides?.customer_label ?? null,
    message: template.message,
    tone: template.tone,
    requires_human_approval: true,
    reason: opportunity.reason,
  };
}

/* ─── 6. buildPostRevenueInsights ─── */

/**
 * Combine post revenue and lost demand by post_url/product_id where available.
 * Identifies high-revenue posts, high-demand/low-conversion posts, and high
 * lost-demand posts. Pure function — no I/O.
 */
export function buildPostRevenueInsights(input: RevenueRecoveryAggregationInput): PostRevenueInsight[] {
  const { postRevenue, postPerformance, lostDemand } = input;
  const insights: PostRevenueInsight[] = [];

  // Lost demand count per post isn't directly available (LostDemandRow has no post url),
  // so we approximate lost demand per post from postPerformance when paid_orders == 0.
  const merged = new Map<
    string,
    {
      post_url: string;
      product_id?: string | null;
      revenue: number | null;
      order_count: number;
      conversations: number;
      conversion_rate: number | null;
      lost_demand_count: number;
    }
  >();

  const mergeRow = (
    post_url: string,
    product_id: string | null,
    patch: Partial<{
      revenue: number | null;
      order_count: number;
      conversations: number;
      conversion_rate: number | null;
      lost_demand_count: number;
    }>,
  ) => {
    const existing = merged.get(post_url) ?? {
      post_url,
      product_id: product_id ?? null,
      revenue: null as number | null,
      order_count: 0,
      conversations: 0,
      conversion_rate: null as number | null,
      lost_demand_count: 0,
    };
    merged.set(post_url, { ...existing, ...patch });
  };

  for (const row of postRevenue ?? []) {
    mergeRow(row.instagram_post_url, row.product_id, {
      revenue: parseMoney(row.revenue),
      order_count: row.paid_orders ?? 0,
      conversations: row.conversations ?? 0,
      conversion_rate: row.conversion_rate ?? null,
      lost_demand_count: Math.max(0, (row.conversations ?? 0) - (row.paid_orders ?? 0)),
    });
  }
  for (const row of postPerformance ?? []) {
    const existing = merged.get(row.instagram_post_url);
    const lostDemandCount = Math.max(0, (row.inbound_messages ?? 0) - (row.paid_orders ?? 0));
    mergeRow(row.instagram_post_url, row.product_id ?? existing?.product_id ?? null, {
      revenue: existing?.revenue ?? parseMoney(row.revenue),
      order_count: existing?.order_count ?? row.paid_orders ?? 0,
      conversations: existing?.conversations ?? row.inbound_messages ?? 0,
      conversion_rate: existing?.conversion_rate ?? row.conversion_rate ?? null,
      lost_demand_count: Math.max(existing?.lost_demand_count ?? 0, lostDemandCount),
    });
  }

  // Reference lostDemand count to flag posts with high lost demand (best-effort by product).
  const lostByProduct = new Map<string, number>();
  for (const row of lostDemand ?? []) {
    if (row.product_id) lostByProduct.set(row.product_id, (lostByProduct.get(row.product_id) ?? 0) + (row.count ?? 0));
  }

  for (const row of merged.values()) {
    const productLost = row.product_id ? lostByProduct.get(row.product_id) ?? 0 : 0;
    const lostDemandCount = Math.max(row.lost_demand_count, productLost);
    const revenue = row.revenue;
    const conversion = row.conversion_rate;

    let insight: string;
    let recommended_action: string;

    if (revenue != null && revenue > 0 && (row.order_count > 0) && (conversion == null || conversion >= LOW_CONVERSION_THRESHOLD)) {
      insight = `High revenue post — ${row.order_count} paid order(s), ≈ ${revenue.toLocaleString()} revenue.`;
      recommended_action = 'Boost or replicate this post; ensure linked product stays in stock.';
    } else if (
      conversion != null &&
      conversion < LOW_CONVERSION_THRESHOLD &&
      row.order_count > 0 &&
      row.conversations >= LOW_CONVERSION_MIN_CONVERSATIONS
    ) {
      insight = `High demand, low conversion — ${row.conversations} conversation(s) at ${(conversion * 100).toFixed(1)}% conversion.`;
      recommended_action = 'Review catalog mapping, pricing, and recovery rules for this post.';
    } else if (lostDemandCount >= HIGH_LOST_DEMAND_THRESHOLD) {
      insight = `High lost demand — ${lostDemandCount} request(s) could not be fulfilled.`;
      recommended_action = 'Restock the linked product and notify waiting customers.';
    } else if (revenue != null && revenue > 0) {
      insight = `Revenue post — ${row.order_count} paid order(s), ≈ ${revenue.toLocaleString()} revenue.`;
      recommended_action = 'Keep this post promoted and monitor stock.';
    } else {
      insight = `Post generated ${row.conversations} conversation(s) with no paid orders yet.`;
      recommended_action = 'Check that the linked product and recovery rules are configured.';
    }

    insights.push({
      post_url: row.post_url,
      post_id: null,
      product_id: row.product_id ?? null,
      revenue,
      order_count: row.order_count,
      demand_count: row.conversations,
      lost_demand_count: lostDemandCount,
      conversion_rate: conversion,
      insight,
      recommended_action,
    });
  }

  // Sort: high revenue first, then high lost demand, then high demand.
  return insights.sort((a, b) => {
    const aScore = (a.revenue ?? 0) + (a.lost_demand_count ?? 0) * 1000 + (a.demand_count ?? 0) * 10;
    const bScore = (b.revenue ?? 0) + (b.lost_demand_count ?? 0) * 1000 + (b.demand_count ?? 0) * 10;
    return bScore - aScore;
  });
}

/* ─── 7. buildRevenueRecoveryDashboard ─── */

/**
 * Compose the full revenue recovery dashboard: opportunities, lost demand
 * insights, restock waitlist, post insights, and headline totals. Pure
 * function — no I/O.
 */
export function buildRevenueRecoveryDashboard(input: RevenueRecoveryAggregationInput): RevenueRecoveryDashboard {
  const opportunities = buildRecoveryOpportunities(input);
  const lostDemand = buildLostDemandInsights(input);
  const restockWaitlist = buildRestockWaitlist(input);
  const postInsights = buildPostRevenueInsights(input);

  const highPriorityCount = opportunities.filter((o) => o.severity === 'high').length;

  let total: number | null = null;
  let hasAnyValue = false;
  for (const op of opportunities) {
    if (op.estimated_value != null) {
      total = (total ?? 0) + op.estimated_value;
      hasAnyValue = true;
    }
  }
  const totalEstimatedRecoverableValue = hasAnyValue ? total : null;

  return {
    opportunities,
    lostDemand,
    restockWaitlist,
    postInsights,
    totalEstimatedRecoverableValue,
    highPriorityCount,
  };
}

/* ─── Testing exports ─── */

export const __testing = {
  parseMoney,
  severityFromValue,
  isAbandonedOrder,
  isUnpaidOrder,
  dedupKey,
  RESTOCK_WAITLIST_THRESHOLD,
};
