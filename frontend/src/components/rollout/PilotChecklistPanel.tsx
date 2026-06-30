import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { Badge, Callout, Card, CardBody, CardHeader } from '../ui';
import { EmptyState, ErrorState, KpiCard, LoadingState } from '../data';
import { apiClient } from '../../services/apiClient';
import { useShopReadiness } from '../../lib/useShopReadiness';
import { loadCachedTrustSummary } from '../../lib/trustEvaluation';
import type { PilotChecklistItem } from '../../types/pilot';

/**
 * Reusable pilot readiness panel. Derives a readiness score, missing
 * requirements, warnings, and recommended next actions deterministically
 * from existing PilotReadiness + PilotMetrics + AgentRiskSettings responses.
 */
export interface PilotChecklistPanelProps {
  shopId: string | null | undefined;
}

function actionForCheck(item: PilotChecklistItem): { label: string; to: string } | null {
  const key = item.key.toLowerCase();
  if (key.includes('webhook') || key.includes('channel') || key.includes('instagram')) {
    return { label: 'Connect a channel', to: '/system/channels' };
  }
  if (key.includes('inventory') || key.includes('catalog') || key.includes('product')) {
    return { label: 'Open Catalog', to: '/catalog/products' };
  }
  if (key.includes('trl') || key.includes('validation') || key.includes('regression')) {
    return { label: 'Run regression', to: '/automation/scenario-simulator' };
  }
  if (key.includes('risk') || key.includes('threshold')) {
    return { label: 'Open Risk settings', to: '/automation/risk' };
  }
  return null;
}

export function PilotChecklistPanel({ shopId }: PilotChecklistPanelProps) {
  const readinessQuery = useQuery({
    queryKey: ['pilot-readiness', shopId],
    queryFn: () => apiClient.getPilotReadiness(shopId!),
    enabled: Boolean(shopId),
  });
  const metricsQuery = useQuery({
    queryKey: ['pilot-metrics', shopId],
    queryFn: () => apiClient.getPilotMetrics(shopId!),
    enabled: Boolean(shopId),
  });
  const riskQuery = useQuery({
    queryKey: ['agent-risk-settings', shopId],
    queryFn: () => apiClient.getAgentRiskSettings(shopId!),
    enabled: Boolean(shopId),
  });

  // Sprint 2 shared shop readiness — rendered as a complementary section above
  // the existing pilot checklist. Fail-open: errors surface a non-blocking
  // callout and the pilot checklist below keeps working unchanged.
  const shopReadinessQuery = useShopReadiness(shopId);

  // Sprint 6 — optional red-team summary from the Trust Center cache. Pure
  // client-side; null when no trust run has been recorded. Non-blocking.
  const trustSummary = loadCachedTrustSummary(shopId);

  const readiness = readinessQuery.data;
  const metrics = metricsQuery.data;

  const { score, missing, warnings, actions } = useMemo(() => {
    const checklist = readiness?.checklist ?? [];
    const total = checklist.length;
    const passed = checklist.filter((item) => item.passed).length;
    const score = total > 0 ? Math.round((passed / total) * 100) : 0;
    const missing = checklist.filter((item) => !item.passed);

    const warnings = [...(readiness?.warnings ?? [])];
    if (metrics && metrics.failed_jobs > 0) {
      warnings.push(`${metrics.failed_jobs} failed job(s) reported by pilot metrics.`);
    }
    if (metrics && metrics.invalid_llm_outputs > 0) {
      warnings.push(`${metrics.invalid_llm_outputs} invalid LLM output(s) reported.`);
    }

    const actions = missing
      .map((item) => actionForCheck(item))
      .filter((action): action is { label: string; to: string } => action !== null);

    return { score, missing, warnings, actions };
  }, [readiness, metrics]);

  if (!shopId) {
    return (
      <Card>
        <CardHeader title="Pilot readiness" description="Select a shop to view readiness." />
        <CardBody>
          <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
        </CardBody>
      </Card>
    );
  }

  if (readinessQuery.isLoading || metricsQuery.isLoading || riskQuery.isLoading) {
    return (
      <Card>
        <CardHeader title="Pilot readiness" />
        <CardBody>
          <LoadingState label="Loading pilot readiness…" />
        </CardBody>
      </Card>
    );
  }

  if (readinessQuery.error) {
    return (
      <Card>
        <CardHeader title="Pilot readiness" />
        <CardBody>
          <ErrorState
            message={
              readinessQuery.error instanceof Error
                ? readinessQuery.error.message
                : 'Failed to load pilot readiness'
            }
          />
        </CardBody>
      </Card>
    );
  }

  if (!readiness) {
    return (
      <Card>
        <CardHeader title="Pilot readiness" />
        <CardBody>
          <EmptyState title="No readiness data" description="Pilot readiness has not been computed for this shop." />
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Pilot readiness"
        description="Readiness score, missing requirements, warnings, and recommended next actions."
        actions={
          <Badge tone={readiness.ready_for_trl6_pilot ? 'success' : 'danger'}>
            {readiness.ready_for_trl6_pilot ? 'Ready for TRL 6' : 'Not ready'}
          </Badge>
        }
      />
      <CardBody className="flex flex-col gap-4">
        {shopReadinessQuery.error ? (
          <Callout title="Shop readiness unavailable">
            Sprint 2 readiness could not be loaded — showing pilot checklist only.
          </Callout>
        ) : null}

        {trustSummary ? (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-surface-sunken p-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-semibold text-fg">Red-team status</span>
              <Badge tone={trustSummary.safeToRollout ? 'success' : 'danger'}>
                {trustSummary.safeToRollout
                  ? `${trustSummary.passed}/${trustSummary.total} passed`
                  : `${trustSummary.criticalFailures + trustSummary.highFailures} blocker(s)`}
              </Badge>
            </div>
            <Link className="text-xs text-accent hover:underline" to="/ai/trust">
              Open Trust Center →
            </Link>
          </div>
        ) : null}

        {shopReadinessQuery.shopReadiness ? (
          <div className="rounded-lg border border-border bg-surface-sunken p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold text-fg">Shop readiness</span>
                <Badge tone={shopReadinessQuery.shopReadiness.score === 100 ? 'success' : shopReadinessQuery.shopReadiness.score >= 50 ? 'warning' : 'danger'}>
                  {shopReadinessQuery.shopReadiness.score}%
                </Badge>
                <Badge tone={shopReadinessQuery.shopReadiness.readyForPilot ? 'success' : 'danger'}>
                  {shopReadinessQuery.shopReadiness.readyForPilot ? 'Pilot ready' : 'Pilot blocked'}
                </Badge>
                <Badge tone={shopReadinessQuery.shopReadiness.readyForAutomation ? 'success' : 'danger'}>
                  {shopReadinessQuery.shopReadiness.readyForAutomation ? 'Automation ready' : 'Automation blocked'}
                </Badge>
              </div>
              <Link className="text-xs text-accent hover:underline" to="/system/readiness">
                Open readiness →
              </Link>
            </div>
            {shopReadinessQuery.shopReadiness.blockingReasons.length > 0 ? (
              <ul className="mt-2 list-inside list-disc space-y-0.5 text-xs text-muted">
                {shopReadinessQuery.shopReadiness.blockingReasons.slice(0, 3).map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs text-muted">No blockers detected across channel, catalog, automation, policy, regression, or operations.</p>
            )}
          </div>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-3">
          <KpiCard
            label="Readiness score"
            value={`${score}%`}
            tone={score === 100 ? 'success' : score >= 50 ? 'warning' : 'danger'}
          />
          <KpiCard
            label="Missing requirements"
            value={String(missing.length)}
            tone={missing.length === 0 ? 'success' : 'warning'}
          />
          <KpiCard
            label="Open warnings"
            value={String(warnings.length)}
            tone={warnings.length === 0 ? 'success' : 'warning'}
          />
        </div>

        {missing.length > 0 ? (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-fg">Missing requirements</h3>
            <ul className="space-y-1.5 text-sm">
              {missing.map((item) => {
                const action = actionForCheck(item);
                return (
                  <li
                    key={item.key}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border bg-surface-sunken px-3 py-2"
                  >
                    <span className="text-fg">{item.label}</span>
                    {action ? (
                      <Link className="text-xs text-accent hover:underline" to={action.to}>
                        {action.label} →
                      </Link>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </div>
        ) : null}

        {warnings.length > 0 ? (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-fg">Warnings</h3>
            <ul className="list-inside list-disc space-y-1 text-sm text-muted">
              {warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {actions.length > 0 ? (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-fg">Recommended next actions</h3>
            <div className="flex flex-wrap gap-2">
              {actions.map((action) => (
                <Link
                  key={`${action.label}-${action.to}`}
                  className="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-accent hover:bg-surface-sunken"
                  to={action.to}
                >
                  {action.label} →
                </Link>
              ))}
            </div>
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}
