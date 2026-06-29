import { Link } from 'react-router-dom';

import { Badge, Card, CardBody, CardHeader } from '../ui';
import { DataTable, EmptyState } from '../data';
import type { Column } from '../data';
import type { BadgeTone } from '../ui';
import type { LostDemandInsight, RevenueRecoverySeverity } from '../../types/sprint4Revenue';

export interface LostDemandTableProps {
  insights: LostDemandInsight[];
  isLoading?: boolean;
  error?: string | null;
  /** Hide the surrounding Card (used when embedded in another Card). */
  bare?: boolean;
}

function severityTone(severity: RevenueRecoverySeverity): BadgeTone {
  if (severity === 'high') return 'danger';
  if (severity === 'medium') return 'warning';
  return 'neutral';
}

function formatMoney(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

const columns: Column<LostDemandInsight>[] = [
  {
    key: 'product',
    header: 'Product / variant',
    render: (row) => {
      const label = row.variant_label
        ? `${row.product_name ?? 'Unknown product'} — ${row.variant_label}`
        : row.product_name ?? 'Unknown product';
      if (row.product_id) {
        return (
          <Link className="font-medium text-accent hover:underline" to={`/catalog/products/${row.product_id}`}>
            {label}
          </Link>
        );
      }
      return <span className="text-fg">{label}</span>;
    },
  },
  {
    key: 'count',
    header: 'Demand',
    align: 'right',
    render: (row) => <span className="tabular-nums">{row.demand_count.toLocaleString()}</span>,
  },
  {
    key: 'reason',
    header: 'Lost reason',
    render: (row) => <span className="text-muted">{row.lost_reason}</span>,
  },
  {
    key: 'value',
    header: 'Est. lost value',
    align: 'right',
    render: (row) => <span className="tabular-nums">{formatMoney(row.estimated_lost_value)}</span>,
  },
  {
    key: 'severity',
    header: 'Severity',
    render: (row) => <Badge tone={severityTone(row.severity)}>{row.severity}</Badge>,
  },
  {
    key: 'action',
    header: 'Action',
    align: 'right',
    render: (row) =>
      row.action_to ? (
        <Link className="text-xs text-accent hover:underline" to={row.action_to}>
          View →
        </Link>
      ) : null,
  },
];

/**
 * Lost demand grouped by product/variant. Renders a DataTable with product
 * link, demand count, lost reason, estimated lost value, severity badge, and
 * an action link. Reused by the Revenue Recovery page and the existing
 * Unavailable Demand page (additive).
 */
export function LostDemandTable({ insights, isLoading, error, bare }: LostDemandTableProps) {
  const table = (
    <DataTable<LostDemandInsight>
      columns={columns}
      rows={insights}
      rowKey={(row) =>
        `${row.product_id ?? 'unknown'}::${row.variant_label ?? 'none'}::${row.lost_reason}`
      }
      isLoading={isLoading}
      error={error ?? null}
      emptyTitle="No lost demand grouped yet"
      emptyDescription="Demand insights appear when the resolver logs unfulfillable requests."
    />
  );

  if (bare) {
    return table;
  }

  return (
    <Card>
      <CardHeader
        title="Lost demand by product / variant"
        description="Repeated unfulfillable requests grouped by product and variant, sorted by severity then demand count."
      />
      <CardBody>
        {insights.length === 0 && !isLoading && !error ? (
          <EmptyState
            title="No lost demand grouped yet"
            description="Demand insights appear when the resolver logs unfulfillable requests."
          />
        ) : (
          table
        )}
      </CardBody>
    </Card>
  );
}
