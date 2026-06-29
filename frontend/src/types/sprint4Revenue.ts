import type { LostDemandRow, PostPerformanceRow, UnavailableDemandRow } from './competitive';
import type { PostRevenueRow, RecoveryRule } from './sprintD';
import type { UnavailableDemandLog } from './fashion';
import type { Order } from './order';
import type { Conversation } from './conversation';
import type { Product } from './product';

/**
 * Sprint 4 — Revenue Recovery & Growth
 *
 * Frontend-only types. These derive purely from existing backend responses
 * (LostDemandRow, UnavailableDemandRow, PostRevenueRow, Order, Conversation,
 * RecoveryRule, Product, UnavailableDemandLog) — no new backend contracts.
 *
 * Sprint 2 types live in `sprint2Readiness.ts` and Sprint 3 types in
 * `sprint3Automation.ts`; both are imported where useful rather than redefined.
 */

export type RevenueRecoveryOpportunityType =
  | 'abandoned_order'
  | 'unavailable_product'
  | 'unavailable_variant'
  | 'unpaid_order'
  | 'high_intent_no_order'
  | 'restock_waitlist'
  | 'post_demand_spike';

export type RevenueRecoverySeverity = 'high' | 'medium' | 'low';

export type RevenueRecoverySource =
  | 'analytics'
  | 'order'
  | 'conversation'
  | 'catalog'
  | 'recovery_rule';

export interface RevenueRecoveryOpportunity {
  id: string;
  type: RevenueRecoveryOpportunityType;
  severity: RevenueRecoverySeverity;
  shop_id: string;
  customer_id?: string | null;
  conversation_id?: string | null;
  order_id?: string | null;
  product_id?: string | null;
  variant_id?: string | null;
  post_url?: string | null;
  title: string;
  reason: string;
  estimated_value?: number | null;
  suggested_action: string;
  action_to?: string;
  created_at?: string | null;
  source: RevenueRecoverySource;
}

export interface LostDemandInsight {
  product_id?: string | null;
  product_name?: string | null;
  variant_id?: string | null;
  variant_label?: string | null;
  demand_count: number;
  lost_reason: string;
  estimated_lost_value?: number | null;
  severity: RevenueRecoverySeverity;
  action_to?: string;
}

export type RestockWaitlistStatus = 'waiting' | 'notified' | 'converted' | 'dismissed';

export interface RestockWaitlistItem {
  id: string;
  customer_id?: string | null;
  conversation_id?: string | null;
  product_id?: string | null;
  variant_id?: string | null;
  product_label: string;
  requested_variant_label?: string | null;
  customer_label?: string | null;
  requested_at?: string | null;
  status: RestockWaitlistStatus;
  suggested_message: string;
}

export type RecoveryMessageTone = 'friendly' | 'professional' | 'urgent';

export interface RecoveryMessageDraft {
  opportunity_id: string;
  channel_provider?: string | null;
  conversation_id?: string | null;
  customer_label?: string | null;
  message: string;
  tone: RecoveryMessageTone;
  requires_human_approval: boolean;
  reason: string;
}

export interface PostRevenueInsight {
  post_url?: string | null;
  post_id?: string | null;
  product_id?: string | null;
  revenue?: number | null;
  order_count?: number;
  demand_count?: number;
  lost_demand_count?: number;
  conversion_rate?: number | null;
  insight: string;
  recommended_action: string;
}

export interface RevenueRecoveryDashboard {
  opportunities: RevenueRecoveryOpportunity[];
  lostDemand: LostDemandInsight[];
  restockWaitlist: RestockWaitlistItem[];
  postInsights: PostRevenueInsight[];
  totalEstimatedRecoverableValue?: number | null;
  highPriorityCount: number;
}

/**
 * Input bundle passed to the pure builders in `lib/revenueRecovery.ts`.
 * Every field is optional so partial data (e.g. missing orders endpoint)
 * still produces a usable partial dashboard. Money fields on the raw rows
 * are strings in the backend contract; the builders parse them safely.
 */
export interface RevenueRecoveryAggregationInput {
  shopId: string;
  lostDemand?: LostDemandRow[] | null;
  unavailableDemand?: UnavailableDemandRow[] | null;
  stockDemand?: { type: 'color' | 'size'; value: string; requests: number }[] | null;
  unavailableDemandLogs?: (UnavailableDemandLog & {
    conversation_id?: string | null;
    customer_id?: string | null;
    requested_at?: string | null;
  })[] | null;
  orders?: Order[] | null;
  recoveryRules?: RecoveryRule[] | null;
  conversations?: Conversation[] | null;
  postRevenue?: PostRevenueRow[] | null;
  postPerformance?: PostPerformanceRow[] | null;
  products?: Product[] | null;
}
