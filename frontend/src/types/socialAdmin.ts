export interface ScenarioRegressionMetrics {
  automation_handled_rate: number;
  llm_fallback_rate: number;
  handoff_rate: number;
  scenario_accuracy: number;
  reference_resolution_accuracy: number;
  product_discovery_accuracy: number;
  unsafe_action_count: number;
  false_order_count: number;
  false_payment_count: number;
}

export interface ScenarioCoverageRow {
  scenario_code: string;
  scenario_name: string;
  description: string;
  supported_providers: string[];
  current_status: string;
  deterministic_handler_exists: boolean;
  LLM_fallback_exists: boolean;
  human_handoff_exists: boolean;
  tests_exist: boolean;
  frontend_support_exists: boolean;
  priority: string;
}

export interface AutomationRuleStep {
  order: number;
  label: string;
  tier: 'deterministic' | 'llm' | 'human';
  detail: string;
}

export interface AdminTask {
  id: string;
  shop_id: string;
  requested_by_user_id: string | null;
  task_type: string;
  input_json: Record<string, unknown>;
  output_json: {
    draft?: string;
    auto_publish?: boolean;
    schema_version?: string;
    task_type?: string;
  };
  status: string;
  requires_approval: boolean;
  approved_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface OperatorCorrection {
  id: string;
  shop_id: string;
  conversation_id: string;
  message_id: string | null;
  correction_type: string;
  before_json: Record<string, unknown>;
  after_json: Record<string, unknown>;
  operator_id: string | null;
  created_at: string;
}

export interface AutomationSuggestion {
  id: string;
  shop_id: string;
  source_correction_id: string | null;
  suggested_rule_json: {
    type?: string;
    title?: string;
    summary?: string;
    rule?: Record<string, unknown>;
    alias?: Record<string, unknown>;
    test?: Record<string, unknown>;
  };
  status: string;
  created_at: string;
}

export interface OperatorCorrectionInput {
  conversation_id: string;
  message_id?: string;
  before_json: Record<string, string | undefined>;
  after_json: Record<string, string | undefined>;
}
