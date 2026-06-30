/**
 * Sprint 6 — Trust, Safety & Red-Team Evaluation Center
 *
 * Frontend-only types. Red-team test packs are deterministic test definitions
 * (no LLM). Evaluation consumes existing Sprint 2/3 surfaces
 * (ShopReadinessScore, ScenarioRegressionMetrics, SimulatorRunDetail,
 * AgentDecisionTrace, PolicyEvaluationResponse) — no new backend contracts.
 */

import type {
  AssembledDecisionTrace,
  PolicyEvaluationResponse,
  SimulatorRunItem,
} from './trust';
import type { AgentDecisionTrace } from './conversation';

export type TrustTestCategory =
  | 'prompt_injection'
  | 'policy_bypass'
  | 'unsafe_discount'
  | 'payment_risk'
  | 'privacy_leak'
  | 'secret_extraction'
  | 'wrong_product'
  | 'wrong_variant'
  | 'fake_order_confirmation'
  | 'refund_or_cancel_abuse'
  | 'human_handoff_required'
  | 'provider_window_violation';

export type TrustTestSeverity = 'critical' | 'high' | 'medium' | 'low';

export type TrustTestExpectedOutcome =
  | 'block'
  | 'handoff'
  | 'preview'
  | 'safe_reply'
  | 'no_order'
  | 'no_payment'
  | 'no_secret'
  | 'ask_clarifying_question';

export interface TrustTestCase {
  id: string;
  title: string;
  category: TrustTestCategory;
  severity: TrustTestSeverity;
  customerMessage: string;
  expectedOutcome: TrustTestExpectedOutcome;
  expectedReason: string;
  productContext?: string | null;
  policyContext?: string | null;
  tags: string[];
}

export interface TrustTestPack {
  id: string;
  name: string;
  description: string;
  category: TrustTestCategory | 'mixed';
  testCases: TrustTestCase[];
  builtIn: boolean;
}

export type TrustEvaluationResultStatus = 'passed' | 'failed' | 'warning' | 'not_run';

export interface TrustEvaluationResult {
  testCaseId: string;
  title: string;
  category: TrustTestCategory;
  severity: TrustTestSeverity;
  status: TrustEvaluationResultStatus;
  expectedOutcome: TrustTestExpectedOutcome;
  actualOutcome?: string | null;
  reason: string;
  recommendedFix?: string | null;
  traceId?: string | null;
  conversationId?: string | null;
  actionTo?: string | null;
}

export interface TrustEvaluationSummary {
  total: number;
  passed: number;
  failed: number;
  warnings: number;
  criticalFailures: number;
  highFailures: number;
  safeToRollout: boolean;
  blockingReasons: string[];
}

export interface TrustEvaluationRun {
  id: string;
  packId: string;
  packName: string;
  startedAt?: string | null;
  completedAt?: string | null;
  summary: TrustEvaluationSummary;
  results: TrustEvaluationResult[];
}

export interface TrustReadinessSignal {
  key: string;
  label: string;
  passed: boolean;
  severity: 'blocker' | 'warning' | 'info';
  detail?: string | null;
  actionTo?: string;
}

/**
 * Input for `classifyActualOutcome`. All fields optional so the same function
 * can grade a live replay item, a production decision trace, or a policy
 * evaluation response. Missing data yields `unknown` (warning, not failure).
 */
export interface TrustActualInput {
  trace?:
    | (Pick<
        AgentDecisionTrace,
        'auto_send_allowed' | 'human_handoff_required' | 'risk_score' | 'reasoning_summary'
      > & {
        requires_preview?: boolean;
      })
    | null;
  assembledTrace?:
    | (Pick<AssembledDecisionTrace, 'trace_id' | 'conversation_id'> & {
      auto_send_allowed?: boolean;
      human_handoff_required?: boolean;
      requires_preview?: boolean;
      risk_score?: { risk_level?: string; requires_handoff?: boolean; requires_preview?: boolean };
    })
    | null;
  replayItem?: Pick<SimulatorRunItem, 'actual_json' | 'expected_json' | 'passed' | 'trace_id' | 'conversation_id'> | null;
  policyResult?: PolicyEvaluationResponse | null;
  autoSendAllowed?: boolean;
  humanHandoffRequired?: boolean;
  requiresPreview?: boolean;
  orderCreated?: boolean;
  paymentCreated?: boolean;
  replyText?: string | null;
}

export type ActualOutcome =
  | 'block'
  | 'handoff'
  | 'preview'
  | 'safe_reply'
  | 'order_created'
  | 'payment_created'
  | 'secret_leak_risk'
  | 'unknown';
