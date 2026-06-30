import type { SimulatorRunItem, SimulatorRunSummary } from './trust';
import type { ScenarioRegressionMetrics } from './socialAdmin';
import type { AgentRiskSettings } from './conversation';
import type { ChannelAccount } from './channel';
import type { PilotSettings } from './pilot';
import type { TrustEvaluationSummary } from './sprint6Trust';

/**
 * Sprint 3 — Automation Adoption
 *
 * Frontend-only types. These derive purely from existing backend responses
 * (AgentDecisionTrace, ScenarioRegressionMetrics, PilotReadinessResponse,
 * TrustSimulatorRunSummary) — no new backend contracts.
 */

export type BlockedReasonCategory =
  | 'risk'
  | 'missing_product_data'
  | 'low_confidence'
  | 'policy_restriction'
  | 'human_handoff_required';

export type CoachSeverity = 'info' | 'warning' | 'danger';

export interface BlockedReason {
  category: BlockedReasonCategory;
  title: string;
  detail: string;
  sourceField: string;
}

export interface AutomationCoachInsight {
  category: BlockedReasonCategory;
  severity: CoachSeverity;
  reason: string;
  impact: string;
  recommendedFix: string;
  actionLabel?: string;
  actionTo?: string;
}

export interface RegressionRunView {
  run: SimulatorRunSummary;
  failedItems: SimulatorRunItem[];
}

export interface RegressionComparison {
  current?: SimulatorRunSummary;
  previous?: SimulatorRunSummary;
  metrics?: ScenarioRegressionMetrics;
  deltas: {
    total?: number;
    passed?: number;
    failed?: number;
  };
}

export type PilotGateCheckKey =
  | 'golden_replay_passed'
  | 'no_critical_failures'
  | 'risk_threshold_ok'
  | 'channel_connected'
  | 'policy_configured'
  | 'no_active_failed_jobs'
  | 'red_team_tests_passed'
  | 'red_team_warnings';

export type GateSeverity = 'blocker' | 'warning';

export interface PilotGateCheck {
  key: PilotGateCheckKey;
  label: string;
  passed: boolean;
  severity: GateSeverity;
  detail: string | null;
  actionLabel?: string;
  actionTo?: string;
}

export interface RolloutGateState {
  checks: PilotGateCheck[];
  ready: boolean;
  blockingReasons: string[];
  readinessScore: number;
}

export interface RolloutGateInput {
  regression?: ScenarioRegressionMetrics | null;
  latestRun?: SimulatorRunSummary | null;
  riskSettings?: AgentRiskSettings | null;
  channels: ChannelAccount[];
  pilot?: PilotSettings | null;
  failedJobsCount: number;
  /**
   * Sprint 6 — optional red-team evaluation summary. When provided, the gate
   * appends a `red_team_tests_passed` blocker (and a `red_team_warnings`
   * warning when there are warnings). When null/undefined, behavior is
   * unchanged from Sprint 3.
   */
  trustEvaluationSummary?: TrustEvaluationSummary | null;
}
