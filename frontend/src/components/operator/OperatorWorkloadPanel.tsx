import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { Badge } from '../ui';
import { Card, CardBody, CardHeader } from '../ui';
import { DataTable, EmptyState, LoadingState, ErrorState } from '../data';
import { apiClient } from '../../services/apiClient';
import { buildOperatorWorkload } from '../../lib/operatorWorkspace';
import { queryKeys } from '../../lib/queryClient';
import type { OperatorQueueItem, OperatorWorkloadRow } from '../../types/sprint5Operator';

interface OperatorWorkloadPanelProps {
  shopId: string;
  queueItems: OperatorQueueItem[];
}

/**
 * Sprint 5 — Operator workload panel. Derives live workload rows from the
 * current queue (assigned count, breached SLA, high-priority count) and
 * augments them with historical analytics (resolved today, avg response time)
 * from `getAnalyticsOperatorPerformance`. Falls back to an empty state when no
 * assignment data is available.
 */
export function OperatorWorkloadPanel({ shopId, queueItems }: OperatorWorkloadPanelProps) {
  const performanceQuery = useQuery({
    queryKey: ['operator-workspace', shopId, 'operator-performance'],
    queryFn: () => apiClient.getAnalyticsOperatorPerformance(shopId),
    enabled: Boolean(shopId),
  });

  const rows = useMemo<OperatorWorkloadRow[]>(() => {
    const historical = (performanceQuery.data?.items ?? []).map((row) => ({
      operator_id: row.operator_id,
      operator_name: row.operator_name,
      resolved_today: row.resolved_conversations,
      avg_response_minutes:
        row.average_response_time_seconds != null
          ? Math.round(row.average_response_time_seconds / 60)
          : null,
    }));
    return buildOperatorWorkload(queueItems, historical);
  }, [queueItems, performanceQuery.data]);

  const hasAssignmentData = queueItems.some(
    (item) => item.assigned_operator_id && item.status !== 'resolved',
  );

  if (performanceQuery.isLoading && queueItems.length === 0) {
    return (
      <Card>
        <CardHeader title="Operator workload" />
        <CardBody>
          <LoadingState label="Loading workload…" />
        </CardBody>
      </Card>
    );
  }

  if (!hasAssignmentData && rows.length === 0) {
    return (
      <Card>
        <CardHeader title="Operator workload" />
        <CardBody>
          <EmptyState
            title="Operator assignment data is not available yet."
            description="Once conversations are assigned to operators, live workload will appear here."
          />
        </CardBody>
      </Card>
    );
  }

  if (performanceQuery.isError && rows.length === 0) {
    return (
      <Card>
        <CardHeader title="Operator workload" />
        <CardBody>
          <ErrorState
            message={
              performanceQuery.error instanceof Error
                ? performanceQuery.error.message
                : 'Failed to load operator performance.'
            }
          />
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Operator workload"
        description="Live assigned counts and SLA risk, augmented with historical performance."
      />
      <CardBody>
        <DataTable
          rows={rows}
          rowKey={(row) => row.operator_id}
          columns={[
            {
              key: 'operator',
              header: 'Operator',
              render: (row) => <span className="font-medium text-fg">{row.operator_name}</span>,
            },
            {
              key: 'assigned',
              header: 'Assigned',
              align: 'right',
              render: (row) => <span className="tabular-nums text-fg">{row.assigned_count}</span>,
            },
            {
              key: 'breached',
              header: 'Breached SLA',
              align: 'right',
              render: (row) =>
                row.breached_sla_count > 0 ? (
                  <Badge tone="danger">{row.breached_sla_count}</Badge>
                ) : (
                  <span className="tabular-nums text-muted">0</span>
                ),
            },
            {
              key: 'high',
              header: 'High priority',
              align: 'right',
              render: (row) =>
                row.high_priority_count && row.high_priority_count > 0 ? (
                  <Badge tone="warning">{row.high_priority_count}</Badge>
                ) : (
                  <span className="tabular-nums text-muted">0</span>
                ),
            },
            {
              key: 'resolved',
              header: 'Resolved (today)',
              align: 'right',
              render: (row) =>
                row.resolved_today_count != null ? (
                  <span className="tabular-nums text-fg">{row.resolved_today_count}</span>
                ) : (
                  <span className="text-subtle">—</span>
                ),
            },
            {
              key: 'avg',
              header: 'Avg response',
              align: 'right',
              render: (row) =>
                row.avg_response_minutes != null ? (
                  <span className="tabular-nums text-fg">{row.avg_response_minutes}m</span>
                ) : (
                  <span className="text-subtle">—</span>
                ),
            },
          ]}
        />
      </CardBody>
    </Card>
  );
}

// Re-export queryKeys for callers that want to invalidate.
export { queryKeys };
