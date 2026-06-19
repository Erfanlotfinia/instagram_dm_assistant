export interface ConversionFunnelMetrics {
  inbound_messages: number;
  product_resolved: number;
  draft_orders: number;
  paid_orders: number;
}

export interface LowStockVariantSummary {
  variant_id: string;
  product_id: string;
  product_title: string;
  sku: string;
  color: string | null;
  size: string | null;
  available_stock: number;
}

export interface DashboardMetrics {
  today_orders: number;
  paid_orders: number;
  waiting_for_payment: number;
  handoff_conversations: number;
  abandoned_orders: number;
  recovered_orders: number;
  recovered_revenue: string;
  upsell_suggestions: number;
  upsell_accepted: number;
  active_conversations: number;
  messages_today: number;
  messages_week: number;
  automation_success_rate: number;
  llm_fallback_rate: number;
  handoff_rate: number;
  failed_jobs_count: number;
  top_selling_posts: TopSellingPostSummary[];
  top_lost_demand_variants: LostDemandVariantSummary[];
  low_stock_variants: LowStockVariantSummary[];
  conversion_funnel: ConversionFunnelMetrics;
}

export interface DashboardTrendPoint {
  date: string;
  messages: number;
  automated: number;
  llm: number;
  handoff: number;
  conversions: number;
  active_conversations: number;
  pending_orders: number;
  failed_jobs: number;
}

export interface DashboardTrends {
  period: string;
  points: DashboardTrendPoint[];
}

export interface TopSellingPostSummary {
  instagram_post_url: string;
  paid_orders: number;
  revenue: string;
}

export interface LostDemandVariantSummary {
  requested_color: string | null;
  requested_size: string | null;
  product_id: string | null;
  count: number;
}
