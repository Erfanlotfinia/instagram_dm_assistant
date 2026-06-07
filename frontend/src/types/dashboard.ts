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
  low_stock_variants: LowStockVariantSummary[];
  conversion_funnel: ConversionFunnelMetrics;
}
