export type PolicyCheckResult = {
  name: string;
  passed: boolean;
  reason?: string | null;
  severity: string;
};

export type PolicyEvaluationResponse = {
  allowed: boolean;
  checks: PolicyCheckResult[];
  blocked_actions: string[];
};

export type TraceEvent = {
  id: string;
  trace_id: string;
  shop_id: string;
  conversation_id?: string | null;
  sequence: number;
  event_type: string;
  payload_json: Record<string, unknown>;
  created_at: string;
};

export type AssembledDecisionTrace = {
  trace_id: string;
  shop_id: string;
  conversation_id?: string | null;
  header: Record<string, unknown>;
  retrieval_evidence: TraceEvent[];
  slots_extracted: TraceEvent[];
  confidence_bands: TraceEvent[];
  policy_checks: TraceEvent[];
  actions_attempted: TraceEvent[];
  actions_blocked: TraceEvent[];
  all_events: TraceEvent[];
};

export type SimulatorRunItem = {
  id: string;
  run_id: string;
  item_key: string;
  input_json: Record<string, unknown>;
  expected_json: Record<string, unknown>;
  actual_json: Record<string, unknown>;
  diff_json: { mismatches?: string[]; passed?: boolean };
  passed: boolean;
  trace_id?: string | null;
  conversation_id?: string | null;
  processing_time_ms: number;
  created_at: string;
};

export type SimulatorRunSummary = {
  id: string;
  shop_id: string;
  label?: string | null;
  source_type: string;
  model_version: string;
  prompt_version: string;
  policy_version_id?: string | null;
  catalog_snapshot_hash: string;
  status: string;
  total_items: number;
  passed_items: number;
  failed_items: number;
  diff_summary_json: Record<string, unknown>;
  started_at: string;
  completed_at?: string | null;
};

export type SimulatorRunDetail = SimulatorRunSummary & {
  items: SimulatorRunItem[];
  catalog_snapshot_json: Record<string, unknown>;
};

export type ReplayScenarioInput = {
  item_key: string;
  message_text: string;
  shared_post_url?: string | null;
  instagram_user_id?: string;
  expected_json?: Record<string, unknown>;
};

export type ReplayRunRequest = {
  label?: string | null;
  model_version?: string | null;
  prompt_version?: string | null;
  policy_version_id?: string | null;
  campaign?: string | null;
  scenarios: ReplayScenarioInput[];
};

export type EmergencyStopScopePreview = {
  active_conversation_count: number;
  simulation_conversation_count: number;
  affected_conversation_ids: string[];
};

export type EmergencyStopResponse = {
  pilot_settings: import('./pilot').PilotSettings;
  event: import('./pilot').PilotEvent;
  scope_preview: EmergencyStopScopePreview;
  incident_id?: string | null;
};

export type ScenarioPack = {
  id: string;
  shop_id: string;
  name: string;
  pack_type: string;
  description?: string | null;
  scenarios_json: Record<string, unknown>[];
  is_golden: boolean;
  created_by_user_id?: string | null;
};

export type IncidentEvent = {
  id: string;
  incident_id: string;
  event_type: string;
  actor_user_id?: string | null;
  description?: string | null;
  metadata_json: Record<string, unknown>;
  affected_conversation_ids: string[];
  created_at: string;
};

export type Incident = {
  id: string;
  shop_id: string;
  title: string;
  severity: string;
  status: string;
  trigger: string;
  opened_by_user_id?: string | null;
  opened_at: string;
  resolved_at?: string | null;
  summary_json: Record<string, unknown>;
  events?: IncidentEvent[];
};
