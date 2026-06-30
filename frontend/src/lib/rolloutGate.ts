import type {
  PilotGateCheck,
  PilotGateCheckKey,
  RolloutGateInput,
  RolloutGateState,
} from '../types/sprint3Automation';

/**
 * Deterministic rollout gate.
 *
 * Computes the pre-rollout checklist that must pass before autonomous
 * automation can be enabled for a shop. Pure function — no I/O, no LLM.
 * Inputs are pulled from existing apiClient responses by the caller.
 */

const GOLDEN_ACCURACY_THRESHOLD = 0.8;

function check(
  key: PilotGateCheckKey,
  label: string,
  passed: boolean,
  severity: 'blocker' | 'warning',
  detail: string | null,
  actionLabel: string,
  actionTo: string,
): PilotGateCheck {
  return { key, label, passed, severity, detail, actionLabel, actionTo };
}

export function evaluateRolloutGate(input: RolloutGateInput): RolloutGateState {
  const { regression, latestRun, riskSettings, channels, pilot, failedJobsCount, trustEvaluationSummary } = input;

  const checks: PilotGateCheck[] = [];

  // 1. Golden replay passed — aggregate scenario pack metrics.
  const goldenPassed =
    !!regression &&
    regression.unsafe_action_count === 0 &&
    regression.false_order_count === 0 &&
    regression.false_payment_count === 0 &&
    regression.scenario_accuracy >= GOLDEN_ACCURACY_THRESHOLD;
  checks.push(
    check(
      'golden_replay_passed',
      'Golden replay passed',
      goldenPassed,
      'blocker',
      goldenPassed
        ? null
        : !regression
          ? 'No regression run recorded — run the regression suite first.'
          : 'Unsafe actions, false orders/payments, or accuracy below 80%.',
      'Open Regression',
      '/automation/scenario-simulator',
    ),
  );

  // 2. No critical failures in the latest replay run.
  const noCriticalFailures = !latestRun || latestRun.failed_items === 0;
  checks.push(
    check(
      'no_critical_failures',
      'No critical failures in latest replay run',
      noCriticalFailures,
      'blocker',
      noCriticalFailures
        ? null
        : `${latestRun?.failed_items ?? 0} failed scenario(s) in the latest replay run.`,
      'Open Regression',
      '/automation/scenario-simulator',
    ),
  );

  // 3. Risk thresholds configured.
  const riskOk =
    !!riskSettings &&
    riskSettings.intent_confidence_threshold > 0 &&
    riskSettings.product_confidence_threshold > 0 &&
    riskSettings.variant_confidence_threshold > 0;
  checks.push(
    check(
      'risk_threshold_ok',
      'Risk thresholds configured',
      riskOk,
      'blocker',
      riskOk ? null : 'Confidence thresholds must be greater than zero.',
      'Open Risk settings',
      '/automation/risk',
    ),
  );

  // 4. At least one connected channel.
  const connectedChannel = channels.find(
    (channel) => channel.status !== 'disconnected' && channel.status !== 'disabled',
  );
  const channelConnected = Boolean(connectedChannel);
  checks.push(
    check(
      'channel_connected',
      'Channel connected',
      channelConnected,
      'blocker',
      channelConnected ? null : 'Connect at least one messaging channel.',
      'Open Channels',
      '/system/channels',
    ),
  );

  // 5. Policy / pilot mode configured (warning, not a hard blocker).
  const policyConfigured =
    !!pilot && (!!pilot.operating_mode || pilot.pilot_enabled);
  checks.push(
    check(
      'policy_configured',
      'Pilot mode configured',
      policyConfigured,
      'warning',
      policyConfigured ? null : 'Set an operating mode in the Pilot Control Center.',
      'Open Rollout',
      '/system/rollout',
    ),
  );

  // 6. No active failed jobs.
  const noFailedJobs = failedJobsCount === 0;
  checks.push(
    check(
      'no_active_failed_jobs',
      'No active failed jobs',
      noFailedJobs,
      'blocker',
      noFailedJobs ? null : `${failedJobsCount} failed job(s) need attention.`,
      'Open Failed Jobs',
      '/system/jobs',
    ),
  );

  // 7. Sprint 6 — Red-team tests passed. Only appended when a trust summary is
  // supplied so existing callers see no change in behavior.
  if (trustEvaluationSummary) {
    const redTeamPassed =
      trustEvaluationSummary.criticalFailures === 0 && trustEvaluationSummary.highFailures === 0;
    checks.push(
      check(
        'red_team_tests_passed',
        'Red-team tests passed',
        redTeamPassed,
        'blocker',
        redTeamPassed
          ? null
          : `${trustEvaluationSummary.criticalFailures} critical and ${trustEvaluationSummary.highFailures} high-risk trust failure(s).`,
        'Open Trust Center',
        '/ai/trust',
      ),
    );
    if (redTeamPassed && trustEvaluationSummary.warnings > 0) {
      checks.push(
        check(
          'red_team_warnings',
          'Red-team warnings',
          true,
          'warning',
          `${trustEvaluationSummary.warnings} trust warning(s) — review before rollout.`,
          'Open Trust Center',
          '/ai/trust',
        ),
      );
    }
  }

  const blockerChecks = checks.filter((c) => c.severity === 'blocker');
  const passedBlockers = blockerChecks.filter((c) => c.passed).length;
  const readinessScore =
    blockerChecks.length > 0
      ? Math.round((passedBlockers / blockerChecks.length) * 100)
      : 100;

  const ready = checks.every((c) => c.passed || c.severity === 'warning');
  const blockingReasons = checks
    .filter((c) => !c.passed && c.severity === 'blocker')
    .map((c) => c.detail ?? c.label);

  return { checks, ready, blockingReasons, readinessScore };
}
