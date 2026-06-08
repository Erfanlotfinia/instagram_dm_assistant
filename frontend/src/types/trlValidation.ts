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
