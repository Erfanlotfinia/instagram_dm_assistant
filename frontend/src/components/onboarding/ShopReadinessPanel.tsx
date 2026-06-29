import { Link } from 'react-router-dom';

import { Badge, Card, CardBody, CardHeader } from '../ui';
import { EmptyState, ErrorState, KpiCard, LoadingState } from '../data';
import type { BadgeTone } from '../ui';
import { useShopReadiness } from '../../lib/useShopReadiness';
import type { ShopReadinessArea, ShopReadinessCheck } from '../../types/sprint2Readiness';

const AREA_LABELS: Record<ShopReadinessArea, string> = {
  channel: 'Channel',
  catalog: 'Catalog',
  automation: 'Automation',
  policy: 'Policy',
  regression: 'Regression',
  operations: 'Operations',
};

const AREA_ORDER: ShopReadinessArea[] = [
  'channel',
  'catalog',
  'automation',
  'policy',
  'regression',
  'operations',
];

function checkTone(check: ShopReadinessCheck): BadgeTone {
  if (check.passed) return 'success';
  if (check.severity === 'blocker') return 'danger';
  if (check.severity === 'warning') return 'warning';
  return 'neutral';
}

function checkLabel(check: ShopReadinessCheck): string {
  if (check.passed) return 'Passed';
  return check.severity === 'blocker' ? 'Blocked' : check.severity === 'warning' ? 'Warning' : 'Info';
}

export interface ShopReadinessPanelProps {
  shopId: string | null | undefined;
}

/**
 * Shop readiness dashboard. Renders the overall readiness score, Ready-for-Pilot
 * and Ready-for-Automation badges, checks grouped by area, blocking reasons, and
 * recommended next actions. Uses the shared `useShopReadiness` hook so the same
 * computation feeds Sprint 3 components.
 */
export function ShopReadinessPanel({ shopId }: ShopReadinessPanelProps) {
  const { data, isLoading, error, shopReadiness, channelStates, catalogScore } = useShopReadiness(shopId);

  // Sprint 4 (non-blocking context): a soft revenue-recovery readiness signal
  // derived from already-computed readiness data. Never blocks automation.
  const revenueRecoveryReady =
    shopReadiness != null &&
    (catalogScore?.score ?? 0) >= 80 &&
    channelStates.some((c) => c.ready);


  if (!shopId) {
    return (
      <Card>
        <CardHeader title="Shop readiness" description="Select a shop to view readiness." />
        <CardBody>
          <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
        </CardBody>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader title="Shop readiness" />
        <CardBody>
          <LoadingState label="Loading shop readiness…" />
        </CardBody>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader title="Shop readiness" />
        <CardBody>
          <ErrorState message={error instanceof Error ? error.message : 'Failed to load shop readiness'} />
        </CardBody>
      </Card>
    );
  }

  if (!data || !shopReadiness) {
    return (
      <Card>
        <CardHeader title="Shop readiness" />
        <CardBody>
          <EmptyState title="No readiness data" description="Readiness could not be computed for this shop." />
        </CardBody>
      </Card>
    );
  }

  const checksByArea = AREA_ORDER.map((area) => ({
    area,
    checks: shopReadiness.checks.filter((c) => c.area === area),
  })).filter((group) => group.checks.length > 0);

  return (
    <Card>
      <CardHeader
        title="Shop readiness"
        description="Aggregates channel, catalog, automation, policy, regression, and operations readiness."
        actions={<Badge tone={shopReadiness.score === 100 ? 'success' : shopReadiness.score >= 50 ? 'warning' : 'danger'}>{shopReadiness.score}%</Badge>}
      />
      <CardBody className="flex flex-col gap-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <KpiCard
            label="Readiness score"
            value={`${shopReadiness.score}%`}
            tone={shopReadiness.score === 100 ? 'success' : shopReadiness.score >= 50 ? 'warning' : 'danger'}
          />
          <KpiCard
            label="Ready for pilot"
            value={shopReadiness.readyForPilot ? 'Yes' : 'No'}
            tone={shopReadiness.readyForPilot ? 'success' : 'danger'}
          />
          <KpiCard
            label="Ready for automation"
            value={shopReadiness.readyForAutomation ? 'Yes' : 'No'}
            tone={shopReadiness.readyForAutomation ? 'success' : 'danger'}
          />
        </div>

        {checksByArea.map((group) => (
          <div key={group.area} className="grid gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">
              {AREA_LABELS[group.area]}
            </h3>
            <ul className="grid gap-2">
              {group.checks.map((check) => (
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
                  {check.actionTo ? (
                    <Link className="text-xs text-accent hover:underline" to={check.actionTo}>
                      Open →
                    </Link>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ))}

        {shopReadiness.blockingReasons.length > 0 ? (
          <div className="rounded-md border border-danger/30 bg-danger-soft/20 px-3 py-2 text-sm text-fg" role="alert">
            <p className="font-medium">Blocking reasons:</p>
            <ul className="mt-1 list-inside list-disc space-y-0.5 text-muted">
              {shopReadiness.blockingReasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {shopReadiness.warnings.length > 0 ? (
          <div className="rounded-md border border-warning/30 bg-warning-soft/20 px-3 py-2 text-sm text-fg" role="note">
            <p className="font-medium">Warnings:</p>
            <ul className="mt-1 list-inside list-disc space-y-0.5 text-muted">
              {shopReadiness.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <Link className="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-accent hover:bg-surface-sunken" to="/system/channels/onboarding">
            Channel onboarding →
          </Link>
          <Link className="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-accent hover:bg-surface-sunken" to="/catalog/products">
            Catalog →
          </Link>
          <Link className="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-accent hover:bg-surface-sunken" to="/automation/risk">
            Risk settings →
          </Link>
        </div>

        {/* Sprint 4 (non-blocking): revenue recovery readiness context. */}
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={revenueRecoveryReady ? 'success' : 'info'}>
              {revenueRecoveryReady ? 'Ready' : 'Info'}
            </Badge>
            <span className="text-sm font-medium text-fg">Revenue recovery readiness</span>
            <span className="text-xs text-muted">
              Catalog ≥ 80%{channelStates.some((c) => c.ready) ? ' + at least one channel ready' : ' + no channel ready'}
            </span>
          </div>
          <Link className="text-xs text-accent hover:underline" to="/analytics/recovery">
            Open →
          </Link>
        </div>
      </CardBody>
    </Card>
  );
}
