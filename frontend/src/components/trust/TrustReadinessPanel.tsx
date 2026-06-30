import { Link } from 'react-router-dom';

import { Badge, Card, CardBody, CardHeader } from '../ui';
import { EmptyState, ErrorState, LoadingState } from '../data';
import type { TrustReadinessSignal } from '../../types/sprint6Trust';

export interface TrustReadinessPanelProps {
  signals: TrustReadinessSignal[];
  loading?: boolean;
  error?: string | null;
}

const severityTone = {
  blocker: 'danger',
  warning: 'warning',
  info: 'success',
} as const;

export function TrustReadinessPanel({ signals, loading, error }: TrustReadinessPanelProps) {
  return (
    <Card>
      <CardHeader
        title="Trust readiness"
        description="Red-team + regression + shop readiness signals that gate higher automation modes."
      />
      <CardBody>
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} />
        ) : signals.length === 0 ? (
          <EmptyState title="No readiness signals" />
        ) : (
          <ul className="flex flex-col gap-2">
            {signals.map((signal) => (
              <li
                key={signal.key}
                className="flex items-start justify-between gap-3 rounded-lg border border-border px-3 py-2"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge tone={severityTone[signal.severity]} dot>
                      {signal.passed ? 'passed' : signal.severity}
                    </Badge>
                    <p className="truncate text-sm font-medium text-fg">{signal.label}</p>
                  </div>
                  {signal.detail ? <p className="mt-1 text-xs text-muted">{signal.detail}</p> : null}
                </div>
                {signal.actionTo ? (
                  <Link className="shrink-0 text-xs text-accent hover:underline" to={signal.actionTo}>
                    Open
                  </Link>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
