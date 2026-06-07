export interface OnboardingStepStatus {
  key: string;
  label: string;
  completed: boolean;
  href: string;
}

export interface OnboardingStatus {
  shop_id: string;
  completed_steps: number;
  total_steps: number;
  progress_percent: number;
  steps: OnboardingStepStatus[];
}

export interface DMSimulatorRequest {
  instagram_account_id: string;
  message_text: string;
  shared_post_url?: string | null;
  instagram_user_id?: string;
}

export interface DMSimulatorResponse {
  conversation_id: string;
  is_simulation: boolean;
  extracted_intent: string | null;
  extracted_slots: Record<string, unknown>;
  product_resolution: Record<string, unknown>;
  variant_resolution: Record<string, unknown>;
  inventory_result: Record<string, unknown>;
  next_state: string;
  suggested_reply: string | null;
  auto_send: boolean;
  preview_required: boolean;
  handoff_required: boolean;
  audit: Array<Record<string, unknown>>;
}

export interface FunnelAnalytics {
  inbound_messages: number;
  resolved_product_rate: number;
  variant_resolved_rate: number;
  draft_order_rate: number;
  payment_conversion_rate: number;
  paid_orders: number;
  revenue: string;
  abandoned_conversations: number;
  top_abandoned_reason: string | null;
  operator_handoff_rate: number;
  average_time_to_first_response_seconds: number | null;
  average_time_to_payment_seconds: number | null;
}

export interface PostPerformanceRow {
  instagram_post_url: string;
  product_id: string | null;
  inbound_messages: number;
  draft_orders: number;
  paid_orders: number;
  revenue: string;
  conversion_rate: number;
}

export interface StockDemandRow {
  type: 'color' | 'size';
  value: string;
  requests: number;
}

export interface HandoffAnalyticsRow {
  reason: string;
  count: number;
  rate: number;
}
