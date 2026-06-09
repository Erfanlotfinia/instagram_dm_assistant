export interface TRLValidationRun {
  id: string;
  shop_id: string;
  status: 'running' | 'completed' | 'failed' | string;
  total_scenarios: number;
  passed_scenarios: number;
  failed_scenarios: number;
  metrics_json: Record<string, unknown>;
  started_at: string;
  completed_at: string | null;
  created_by_user_id: string | null;
}

export interface TRLValidationScenarioResult {
  id: string;
  run_id: string;
  scenario_id: string;
  input_json: Record<string, unknown>;
  expected_json: Record<string, unknown>;
  actual_json: Record<string, unknown>;
  passed: boolean;
  failure_reasons: string[];
  processing_time_ms: number;
  conversation_id: string | null;
  order_id: string | null;
  created_at: string;
}

export interface TRLRiskMetrics {
  invalid_llm_json_count: number;
  safe_fallback_count: number;
  human_handoff_count: number;
  false_positive_order_creation: number;
  false_positive_auto_send: number;
  average_risk_score: number;
  critical_risk_count: number;
  scenario_pass_rate_by_category: Record<string, number>;
  average_processing_latency: number;
  p95_processing_latency: number;
}
