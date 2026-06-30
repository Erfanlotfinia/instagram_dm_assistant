import { useState } from 'react';
import { Link } from 'react-router-dom';

import { Badge, Button, Card, CardHeader } from '../ui';
import { DataTable, EmptyState } from '../data';
import type { Column } from '../data';
import type { BadgeTone } from '../ui';
import type { TrustEvaluationResult, TrustTestSeverity } from '../../types/sprint6Trust';

export interface TrustFailureTableProps {
  results: TrustEvaluationResult[];
  loading?: boolean;
  error?: string | null;
}

const severityTone: Record<TrustTestSeverity, BadgeTone> = {
  critical: 'danger',
  high: 'warning',
  medium: 'info',
  low: 'neutral',
};

export function TrustFailureTable({ results, loading, error }: TrustFailureTableProps) {
  const [search, setSearch] = useState('');
  const failed = results.filter((r) => r.status === 'failed' || r.status === 'warning');
  const filtered = failed.filter((r) =>
    search ? `${r.title} ${r.category}`.toLowerCase().includes(search.toLowerCase()) : true,
  );

  const columns: Column<TrustEvaluationResult>[] = [
    {
      key: 'severity',
      header: 'Severity',
      render: (r) => <Badge tone={severityTone[r.severity]}>{r.severity}</Badge>,
    },
    { key: 'category', header: 'Category', render: (r) => r.category },
    { key: 'title', header: 'Test', render: (r) => r.title },
    { key: 'expected', header: 'Expected', render: (r) => r.expectedOutcome },
    { key: 'actual', header: 'Actual', render: (r) => r.actualOutcome ?? '—' },
    {
      key: 'fix',
      header: 'Recommended fix',
      render: (r) => <span className="line-clamp-2 text-xs text-muted">{r.recommendedFix ?? '—'}</span>,
    },
    {
      key: 'action',
      header: 'Action',
      align: 'right',
      render: (r) => (
        <div className="flex justify-end gap-2">
          {r.traceId || r.conversationId ? (
            <Link
              className="text-xs text-accent hover:underline"
              to={r.conversationId ? `/inbox/${r.conversationId}/intelligence` : '/ai/logs'}
            >
              View trace
            </Link>
          ) : null}
          {r.actionTo ? (
            <Link className="text-xs text-accent hover:underline" to={r.actionTo}>
              Go to fix
            </Link>
          ) : null}
          <Button
            variant="ghost"
            size="sm"
            type="button"
            onClick={() => void navigator.clipboard?.writeText(JSON.stringify(r, null, 2))}
          >
            Copy
          </Button>
        </div>
      ),
    },
  ];

  return (
    <Card>
      <CardHeader
        title="Failed tests"
        description="Critical and high-severity trust test failures, with recommended fixes."
        actions={<Badge tone="danger">{failed.length}</Badge>}
      />
      <div className="px-5 py-3">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter by test or category…"
          className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg placeholder:text-subtle"
        />
      </div>
      {error ? (
        <div className="px-6 py-12 text-center text-sm text-danger" role="alert">
          {error}
        </div>
      ) : loading ? (
        <div className="px-6 py-12 text-center text-sm text-muted" role="status">
          Loading…
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No failed tests"
          description="All evaluated trust tests passed or have not been run yet."
        />
      ) : (
        <DataTable columns={columns} rows={filtered} rowKey={(r) => r.testCaseId} />
      )}
    </Card>
  );
}
