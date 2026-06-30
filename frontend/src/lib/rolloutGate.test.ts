import { describe, expect, it } from 'vitest';

import { evaluateRolloutGate } from './rolloutGate';
import type { RolloutGateInput } from '../types/sprint3Automation';
import type { ScenarioRegressionMetrics } from '../types/socialAdmin';
import type { SimulatorRunSummary } from '../types/trust';
import type { AgentRiskSettings } from '../types/conversation';
import type { ChannelAccount } from '../types/channel';
import type { PilotSettings } from '../types/pilot';

function passingRegression(): ScenarioRegressionMetrics {
  return {
    automation_handled_rate: 0.9,
    llm_fallback_rate: 0.05,
    handoff_rate: 0.05,
    scenario_accuracy: 0.85,
    reference_resolution_accuracy: 0.9,
    product_discovery_accuracy: 0.9,
    unsafe_action_count: 0,
    false_order_count: 0,
    false_payment_count: 0,
  };
}

function passingRiskSettings(): AgentRiskSettings {
  return {
    shop_id: 's1',
    intent_confidence_threshold: 0.6,
    slot_confidence_threshold: 0.6,
    product_confidence_threshold: 0.6,
    variant_confidence_threshold: 0.6,
    address_confidence_threshold: 0.6,
    high_value_order_threshold: 100,
    handoff_for_high_risk: true,
    handoff_for_low_variant_confidence: true,
    preview_required_for_high_value_order: true,
  };
}

function connectedChannel(): ChannelAccount {
  return {
    id: 'ch1',
    shop_id: 's1',
    provider: 'instagram',
    display_name: 'IG',
    status: 'connected',
    capabilities_json: {},
    settings_json: {},
    token_configured: true,
    bot_token_configured: false,
    webhook_secret_configured: true,
    created_at: '2026-06-29T00:00:00Z',
    updated_at: '2026-06-29T00:00:00Z',
  };
}

function pilotSettings(overrides: Partial<PilotSettings> = {}): PilotSettings {
  return {
    shop_id: 's1',
    pilot_enabled: true,
    pilot_name: 'Pilot',
    pilot_start_date: null,
    pilot_end_date: null,
    max_auto_sent_messages_per_day: 10,
    max_auto_created_orders_per_day: 5,
    require_operator_approval_for_first_50_orders: true,
    allowed_instagram_account_ids: ['ig1'],
    allowed_product_ids: null,
    emergency_stop_enabled: false,
    operating_mode: 'copilot',
    created_at: '2026-06-29T00:00:00Z',
    updated_at: '2026-06-29T00:00:00Z',
    ...overrides,
  };
}

function run(overrides: Partial<SimulatorRunSummary> = {}): SimulatorRunSummary {
  return {
    id: 'r1',
    shop_id: 's1',
    label: 'run',
    source_type: 'scenario_pack',
    model_version: 'm1',
    prompt_version: 'p1',
    policy_version_id: null,
    catalog_snapshot_hash: 'h',
    status: 'completed',
    total_items: 10,
    passed_items: 10,
    failed_items: 0,
    diff_summary_json: {},
    started_at: '2026-06-29T00:00:00Z',
    completed_at: '2026-06-29T00:01:00Z',
    ...overrides,
  };
}

function allPassInput(overrides: Partial<RolloutGateInput> = {}): RolloutGateInput {
  return {
    regression: passingRegression(),
    latestRun: run(),
    riskSettings: passingRiskSettings(),
    channels: [connectedChannel()],
    pilot: pilotSettings(),
    failedJobsCount: 0,
    ...overrides,
  };
}

describe('evaluateRolloutGate', () => {
  it('is ready when every blocker passes (warning may still fail)', () => {
    const state = evaluateRolloutGate(
      allPassInput({ pilot: pilotSettings({ operating_mode: undefined, pilot_enabled: false }) }),
    );
    expect(state.ready).toBe(true);
    expect(state.readinessScore).toBe(100);
    expect(state.blockingReasons).toEqual([]);
    // policy_configured is a warning and may fail without blocking readiness.
    const policy = state.checks.find((c) => c.key === 'policy_configured');
    expect(policy?.severity).toBe('warning');
    expect(policy?.passed).toBe(false);
  });

  it('blocks when golden replay is missing', () => {
    const state = evaluateRolloutGate(allPassInput({ regression: null }));
    expect(state.ready).toBe(false);
    expect(state.blockingReasons.some((r) => /regression/i.test(r))).toBe(true);
  });

  it('blocks when unsafe actions are present', () => {
    const state = evaluateRolloutGate(
      allPassInput({
        regression: { ...passingRegression(), unsafe_action_count: 2 },
      }),
    );
    expect(state.ready).toBe(false);
  });

  it('blocks when scenario accuracy is below threshold', () => {
    const state = evaluateRolloutGate(
      allPassInput({ regression: { ...passingRegression(), scenario_accuracy: 0.7 } }),
    );
    expect(state.ready).toBe(false);
  });

  it('blocks when the latest replay run has failures', () => {
    const state = evaluateRolloutGate(allPassInput({ latestRun: run({ failed_items: 3 }) }));
    expect(state.ready).toBe(false);
    expect(state.blockingReasons.some((r) => /3 failed scenario/i.test(r))).toBe(true);
  });

  it('blocks when risk thresholds are not configured', () => {
    const state = evaluateRolloutGate(
      allPassInput({ riskSettings: { ...passingRiskSettings(), intent_confidence_threshold: 0 } }),
    );
    expect(state.ready).toBe(false);
  });

  it('blocks when no channel is connected', () => {
    const state = evaluateRolloutGate(allPassInput({ channels: [] }));
    expect(state.ready).toBe(false);
    expect(state.blockingReasons.some((r) => /connect at least one/i.test(r))).toBe(true);
  });

  it('blocks when a connected channel is disconnected', () => {
    const state = evaluateRolloutGate({
      ...allPassInput(),
      channels: [{ ...connectedChannel(), status: 'disconnected' }],
    });
    expect(state.ready).toBe(false);
  });

  it('blocks when there are active failed jobs', () => {
    const state = evaluateRolloutGate(allPassInput({ failedJobsCount: 4 }));
    expect(state.ready).toBe(false);
    expect(state.blockingReasons.some((r) => /4 failed job/i.test(r))).toBe(true);
  });

  it('computes a partial readiness score when some blockers fail', () => {
    const state = evaluateRolloutGate(allPassInput({ channels: [], failedJobsCount: 2 }));
    const blockers = state.checks.filter((c) => c.severity === 'blocker');
    const passed = blockers.filter((c) => c.passed).length;
    expect(state.readinessScore).toBe(Math.round((passed / blockers.length) * 100));
    expect(state.ready).toBe(false);
  });

  it('treats a missing latest run as no-critical-failures passed', () => {
    const state = evaluateRolloutGate(allPassInput({ latestRun: null }));
    const noFailures = state.checks.find((c) => c.key === 'no_critical_failures');
    expect(noFailures?.passed).toBe(true);
  });

  it('does not add red-team checks when trust summary is absent (Sprint 3 behavior preserved)', () => {
    const state = evaluateRolloutGate(allPassInput({ trustEvaluationSummary: null }));
    expect(state.checks.find((c) => c.key === 'red_team_tests_passed')).toBeUndefined();
    expect(state.checks.find((c) => c.key === 'red_team_warnings')).toBeUndefined();
    expect(state.ready).toBe(true);
  });

  it('blocks when trust summary has critical failures', () => {
    const state = evaluateRolloutGate(
      allPassInput({
        trustEvaluationSummary: {
          total: 5,
          passed: 3,
          failed: 2,
          warnings: 0,
          criticalFailures: 1,
          highFailures: 1,
          safeToRollout: false,
          blockingReasons: ['Case A', 'Case B'],
        },
      }),
    );
    const redTeam = state.checks.find((c) => c.key === 'red_team_tests_passed');
    expect(redTeam?.severity).toBe('blocker');
    expect(redTeam?.passed).toBe(false);
    expect(state.ready).toBe(false);
  });

  it('passes with a warning-only trust summary and appends a red_team_warnings check', () => {
    const state = evaluateRolloutGate(
      allPassInput({
        trustEvaluationSummary: {
          total: 5,
          passed: 4,
          failed: 0,
          warnings: 1,
          criticalFailures: 0,
          highFailures: 0,
          safeToRollout: true,
          blockingReasons: [],
        },
      }),
    );
    const redTeam = state.checks.find((c) => c.key === 'red_team_tests_passed');
    expect(redTeam?.passed).toBe(true);
    const warn = state.checks.find((c) => c.key === 'red_team_warnings');
    expect(warn?.severity).toBe('warning');
    expect(state.ready).toBe(true);
  });
});
