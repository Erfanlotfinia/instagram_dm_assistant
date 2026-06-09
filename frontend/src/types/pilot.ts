export interface PilotSettings {
  shop_id: string;
  pilot_enabled: boolean;
  pilot_name: string;
  pilot_start_date: string | null;
  pilot_end_date: string | null;
  max_auto_sent_messages_per_day: number;
  max_auto_created_orders_per_day: number;
  require_operator_approval_for_first_50_orders: boolean;
  allowed_instagram_account_ids: string[];
  allowed_product_ids: string[] | null;
  emergency_stop_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface PilotChecklistItem {
  key: string;
  label: string;
  passed: boolean;
  detail: string | null;
}

export interface PilotReadinessResponse {
  shop_id: string;
  ready_for_trl6_pilot: boolean;
  checklist: PilotChecklistItem[];
  criteria: PilotChecklistItem[];
  latest_trl_validation: Record<string, unknown> | null;
  pilot_settings: PilotSettings;
  warnings: string[];
}

export interface PilotMetrics {
  inbound_messages: number;
  auto_sent_messages: number;
  previewed_messages: number;
  human_handoff_count: number;
  draft_orders: number;
  confirmed_orders: number;
  paid_orders: number;
  cancelled_orders: number;
  failed_jobs: number;
  invalid_llm_outputs: number;
  average_response_time_ms: number;
  p95_response_time_ms: number;
  operator_takeover_count: number;
}

export interface PilotEvent {
  id: string;
  shop_id: string;
  event_type: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  title: string;
  description: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface PilotEventLog {
  events: PilotEvent[];
}

export interface PilotActionResponse {
  pilot_settings: PilotSettings;
  event: PilotEvent;
}
