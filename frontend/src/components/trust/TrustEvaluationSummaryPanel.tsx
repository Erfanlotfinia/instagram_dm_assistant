import { Badge, Card, CardBody, CardHeader, StatusBanner } from '../ui';
import { EmptyState, ErrorState, LoadingState } from '../data';
import type { TrustEvaluationSummary } from '../../types/sprint6Trust';

export interface TrustEvaluationSummaryPanelProps {
  summary: TrustEvaluationSummary | null;
  loading?: boolean;
  error?: string | null;
  packName?: string | null;
}

export function TrustEvaluationSummaryPanel({
  summary,
  loading,
  error,
  packName,
}: TrustEvaluationSummaryPanelProps) {
  return (
    <Card>
      <CardHeader
        title="Latest evaluation result"
        description={packName ? `Pack: ${packName}` : 'Most recent red-team evaluation summary.'}
        actions={summary ? <Badge tone={summary.safeToRollout ? 'success' : 'danger'}>
          {summary.safeToRollout ? 'Safe to rollout' : 'Blocked'}
        </Badge> : null}
      />
      <CardBody>
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} />
        ) : !summary || summary.total === 0 ? (
          <EmptyState
            title="No evaluation run yet"
            description="Run a built-in red-team pack to see pass/fail counts and blockers."
          />
        ) : (
          <div className="flex flex-col gap-4">
            <StatusBanner
              tone={summary.safeToRollout ? 'ok' : 'failed'}
              title={summary.safeToRollout ? 'No critical or high-risk failures' : 'Rollout blocked by trust failures'}
              description={
                summary.safeToRollout
                  ? `${summary.passed}/${summary.total} cases passed. Warnings: ${summary.warnings}.`
                  : `${summary.criticalFailures} critical and ${summary.highFailures} high-risk failure(s) must be fixed.`
              }
            />
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Metric label="Total" value={summary.total} />
              <Metric label="Passed" value={summary.passed} tone="success" />
              <Metric label="Failed" value={summary.failed} tone="danger" />
              <Metric label="Warnings" value={summary.warnings} tone="warning" />
            </div>
            {summary.blockingReasons.length > 0 ? (
              <div className="rounded-lg border border-danger/30 bg-danger-soft p-3">
                <p className="text-xs font-semibold text-danger">Blockers</p>
                <ul className="mt-1 list-disc pl-4 text-xs text-danger">
                  {summary.blockingReasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function Metric({
  label,
  value,
  tone = 'neutral',
}: {
  label: string;
  value: number;
  tone?: 'neutral' | 'success' | 'danger' | 'warning';
}) {
  const toneClass =
    tone === 'success'
      ? 'text-success'
      : tone === 'danger'
        ? 'text-danger'
        : tone === 'warning'
          ? 'text-warning'
          : 'text-fg';
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2">
      <p className="text-xs text-muted">{label}</p>
      <p className={`text-xl font-semibold tabular-nums ${toneClass}`}>{value}</p>
    </div>
  );
}
