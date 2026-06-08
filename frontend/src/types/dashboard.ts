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
  top_selling_posts: TopSellingPostSummary[];
  top_lost_demand_variants: LostDemandVariantSummary[];
  low_stock_variants: LowStockVariantSummary[];
  conversion_funnel: ConversionFunnelMetrics;
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
