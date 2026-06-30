import { Link } from 'react-router-dom';

import { Badge, Button, Callout, Card, CardBody, CardHeader } from '../ui';
import { EmptyState } from '../data';
import type { BadgeTone } from '../ui';
import type { PilotGateCheck, RolloutGateState } from '../../types/sprint3Automation';
import type { ShopReadinessScore } from '../../types/sprint2Readiness';
import type { TrustEvaluationSummary } from '../../types/sprint6Trust';

function checkTone(check: PilotGateCheck): BadgeTone {
  if (check.passed) return 'success';
  return check.severity === 'blocker' ? 'danger' : 'warning';
}

function checkLabel(check: PilotGateCheck): string {
  if (check.passed) return 'Passed';
  return check.severity === 'blocker' ? 'Blocked' : 'Warning';
}

export interface RolloutGateChecklistProps {
  state: RolloutGateState | null;
  /** True while gate inputs are still loading. */
  loading?: boolean;
  /** Called when the operator clicks "Enable Automation" and the gate is ready. */
  onEnableAutomation?: () => void;
  /** True while the enable mutation is in flight. */
  enabling?: boolean;
  /** Whether the shop is currently in an autonomous mode (controls button label). */
  automationEnabled?: boolean;
  /**
   * Optional Sprint 2 shop readiness. When supplied (and loaded without error),
   * the gate appends the readiness checks beneath the existing Sprint 3 checks
   * and merges `readyForAutomation` + blocking reasons. When null/undefined,
   * behavior is unchanged from Sprint 3.
   */
  shopReadiness?: ShopReadinessScore | null;
  /** True while `shopReadiness` is still loading (gate keeps Sprint 3 behavior until it loads). */
  shopReadinessLoading?: boolean;
  /**
   * Sprint 6 — optional red-team evaluation summary. The gate state already
   * includes the red-team check when the caller passed this into
   * `evaluateRolloutGate`; this prop only drives a non-blocking loading
   * callout. When null/undefined, behavior is unchanged.
   */
  trustEvaluationSummary?: TrustEvaluationSummary | null;
  /** True while the trust summary is being loaded. */
  trustEvaluationLoading?: boolean;
}

/**
 * Pre-rollout regression gate. Renders the 6 deterministic checks and gates
 * the "Enable Automation" CTA: the button is disabled while any blocker fails,
 * with the blocking reasons listed below.
 */
export function RolloutGateChecklist({
  state,
  loading,
  onEnableAutomation,
  enabling,
  automationEnabled,
  shopReadiness,
  shopReadinessLoading,
  trustEvaluationSummary,
  trustEvaluationLoading,
}: RolloutGateChecklistProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader
          title="Rollout readiness gate"
          description="Verifies golden replay, risk, channel, policy, and job health before autonomous automation can be enabled."
        />
        <CardBody>
          <EmptyState title="Loading gate status…" description="Checking regression, risk, channel, and job health." />
        </CardBody>
      </Card>
    );
  }

  if (!state) {
    return (
      <Card>
        <CardHeader title="Rollout readiness gate" />
        <CardBody>
          <EmptyState title="Select a shop" description="Use the shop switcher to evaluate rollout readiness." />
        </CardBody>
      </Card>
    );
  }

  // Sprint 2 augmentation: only applies when shop readiness has loaded without
  // error. While loading or errored, keep Sprint 3 behavior unchanged.
  const readinessReady = !shopReadinessLoading && shopReadiness
    ? shopReadiness.readyForAutomation
    : null;
  const effectiveReady = readinessReady === null ? state.ready : state.ready && readinessReady;
  const readinessBlockers =
    shopReadiness && !shopReadinessLoading
      ? shopReadiness.blockingReasons.filter((reason) => !state.blockingReasons.includes(reason))
      : [];

  const ready = effectiveReady;

  return (
    <Card>
      <CardHeader
        title="Rollout readiness gate"
        description="Autonomous automation can only be enabled when every blocker passes."
        actions={
          <Badge tone={ready ? 'success' : 'danger'}>
            {state.readinessScore}% ready
          </Badge>
        }
      />
      <CardBody className="flex flex-col gap-4">
        <ul className="grid gap-2">
          {state.checks.map((check) => (
            <li
              key={check.key}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2"
            >
              <div className="grid gap-0.5">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={checkTone(check)}>{checkLabel(check)}</Badge>
                  <span className="text-sm font-medium text-fg">{check.label}</span>
                </div>
                {check.detail ? (
                  <span className="text-xs text-muted">{check.detail}</span>
                ) : null}
              </div>
              {check.actionLabel && check.actionTo ? (
                <Link className="text-xs text-accent hover:underline" to={check.actionTo}>
                  {check.actionLabel} →
                </Link>
              ) : null}
            </li>
          ))}
        </ul>

        {trustEvaluationLoading ? (
          <Callout title="Evaluating red-team tests…">
            The Trust Center is grading the latest red-team run. The gate will update when results are ready.
          </Callout>
        ) : trustEvaluationSummary ? (
          <div className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-surface-sunken px-3 py-2 text-xs text-muted">
            <span>Red-team status:</span>
            <Badge tone={trustEvaluationSummary.safeToRollout ? 'success' : 'danger'}>
              {trustEvaluationSummary.safeToRollout
                ? `${trustEvaluationSummary.passed}/${trustEvaluationSummary.total} passed`
                : `${trustEvaluationSummary.criticalFailures + trustEvaluationSummary.highFailures} blocker(s)`}
            </Badge>
            <Link className="text-accent hover:underline" to="/ai/trust">
              Open Trust Center →
            </Link>
          </div>
        ) : null}

        {shopReadiness && !shopReadinessLoading ? (
          <div className="grid gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">
              Shop readiness (Sprint 2)
            </h3>
            <ul className="grid gap-2">
              {shopReadiness.checks.map((check) => (
                <li
                  key={check.key}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-surface-sunken px-3 py-2"
                >
                  <div className="grid gap-0.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={check.passed ? 'success' : check.severity === 'blocker' ? 'danger' : 'warning'}>
                        {check.passed ? 'Passed' : check.severity === 'blocker' ? 'Blocked' : 'Warning'}
                      </Badge>
                      <span className="text-sm font-medium text-fg">{check.label}</span>
                    </div>
                    {check.detail ? (
                      <span className="text-xs text-muted">{check.detail}</span>
                    ) : null}
                  </div>
                  {check.actionTo ? (
                    <Link className="text-xs text-accent hover:underline" to={check.actionTo}>
                      Open →
                    </Link>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="flex flex-col gap-2">
          <Button
            type="button"
            disabled={!ready || enabling}
            onClick={onEnableAutomation}
          >
            {enabling
              ? 'Enabling…'
              : automationEnabled
                ? 'Re-activate autonomous mode'
                : 'Enable automation'}
          </Button>
          {!ready ? (
            <div className="rounded-md border border-danger/30 bg-danger-soft/20 px-3 py-2 text-sm text-fg" role="alert">
              <p className="font-medium">Blocking reasons:</p>
              <ul className="mt-1 list-inside list-disc space-y-0.5 text-muted">
                {state.blockingReasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
                {readinessBlockers.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </CardBody>
    </Card>
  );
}
