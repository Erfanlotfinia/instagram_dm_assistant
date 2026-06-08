export interface OnboardingStepStatus {
  key: string;
  label: string;
  completed: boolean;
  href: string;
}

export interface OnboardingStatus {
  shop_id: string;
  completed_steps: string[];
  missing_steps: string[];
  progress_percent: number;
  next_recommended_action: string;
  steps: OnboardingStepStatus[];
  total_steps: number;
}

export interface DMSimulatorRequest {
  instagram_account_id: string;
  message_text: string;
  shared_post_url?: string | null;
  instagram_user_id?: string;
}

export interface DMSimulatorResponse {
  conversation_id: string;
  message_id: string;
  is_simulation: boolean;
  intent: string | null;
  extracted_slots: Record<string, unknown>;
  product_resolution: Record<string, unknown>;
  variant_resolution: Record<string, unknown>;
  inventory_result: Record<string, unknown>;
  next_state: string;
  suggested_reply: string | null;
  auto_send_decision: Record<string, unknown>;
  handoff_reason: string | null;
  draft_order: Record<string, unknown> | null;
  decision_trace: Record<string, unknown>;
}

export interface SimulatorRunSummary {
  conversation_id: string;
  message_id: string | null;
  created_at: string;
  intent: string | null;
  next_state: string | null;
  suggested_reply: string | null;
  message_preview: string | null;
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

export interface TriggerRule {
  id: string;
  shop_id: string;
  instagram_account_id: string;
  instagram_media_id: string | null;
  source_type: 'comment' | 'story_reply' | 'reel_comment' | 'direct_dm' | 'ad_comment';
  keyword: string;
  response_template: string;
  target_product_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TriggerPerformance {
  trigger_id: string;
  keyword: string;
  source_type: TriggerRule['source_type'];
  impressions: number;
  dm_sent: number;
  paid_orders: number;
  revenue: string;
  conversion_rate: number;
}

export interface AgentStudioSettings {
  shop_id: string;
  mode: 'copilot' | 'controlled_autopilot' | 'human_first';
  auto_send_enabled: boolean;
  preview_required_for_low_confidence: boolean;
  preview_required_for_first_order: boolean;
  preview_required_for_high_value_order: boolean;
  confidence_threshold_intent: string;
  confidence_threshold_product: string;
  confidence_threshold_variant: string;
  confidence_threshold_address: string;
  high_value_order_threshold: string;
  brand_voice: string | null;
  selling_style: 'friendly' | 'formal' | 'concise' | 'promotional' | 'educational' | 'balanced';
  discount_policy_json: Record<string, unknown>;
  handoff_policy_json: Record<string, unknown>;
}

export interface UnavailableDemandRow {
  requested_color: string | null;
  requested_size: string | null;
  product_id: string | null;
  count: number;
  lost_revenue_estimate: string;
}

export interface ResponseTimeAnalytics {
  average_first_response_time_seconds: number | null;
  average_time_to_draft_order_seconds: number | null;
  average_time_to_payment_seconds: number | null;
}
