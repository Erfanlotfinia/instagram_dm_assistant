import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { filterBySearch, Pagination, paginateItems } from '../components/Pagination';
import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Select } from '../components/ui';
import { DataTable, EmptyState, FilterBar, KpiCard, LoadingState } from '../components/data';
import type { Column } from '../components/data';
import type { BadgeTone } from '../components/ui';
import { LostDemandTable } from '../components/revenue/LostDemandTable';
import { buildLostDemandInsights } from '../lib/revenueRecovery';
import type { RevenueRecoveryAggregationInput } from '../types/sprint4Revenue';
import type { LostDemandRow } from '../types/competitive';
import { cn } from '../lib/cn';
import { useShop } from '../contexts/ShopContext';
import { queryKeys } from '../lib/queryClient';
import { demandReasonTone, formatMismatchReason } from '../lib/variantResolver';
import { apiClient } from '../services/apiClient';
import type { UnavailableDemandLog } from '../types/fashion';

const PAGE_SIZE = 12;

const ghostLinkClass = 'text-sm font-medium text-accent hover:underline';

function formatMoney(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }
  return value.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function ReasonBadge({ reason }: { reason: string }) {
  const tone = demandReasonTone(reason) as BadgeTone;
  return <Badge tone={tone}>{formatMismatchReason(reason)}</Badge>;
}

function SlotValue({
  raw,
  normalized,
}: {
  raw?: string | null;
  normalized?: string | null;
}) {
  if (!raw && !normalized) {
    return <span className="text-subtle">—</span>;
  }

  if (!raw || raw === normalized) {
    return <span className="text-fg">{normalized ?? raw}</span>;
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-1 text-sm">
      <span className="text-muted">{raw}</span>
      <span className="text-subtle" aria-hidden="true">
        →
      </span>
      <span className="text-fg">{normalized ?? '?'}</span>
    </span>
  );
}

function buildSearchText(
  row: UnavailableDemandLog,
  productName: string | undefined,
): string {
  return [
    row.reason,
    formatMismatchReason(row.reason),
    row.requested_color_raw,
    row.requested_color_normalized,
    row.requested_size_raw,
    row.requested_size_normalized,
    productName,
    row.product_id,
  ]
    .filter(Boolean)
    .join(' ');
}

const REASON_BAR_CLASS: Record<BadgeTone, string> = {
  neutral: 'bg-muted',
  accent: 'bg-accent',
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
  info: 'bg-info',
};

export function UnavailableDemandPage() {
  const { selectedShop, selectedShopId } = useShop();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [reasonFilter, setReasonFilter] = useState('');

  const demandQuery = useQuery({
    queryKey: ['unavailable-demand-logs', selectedShopId],
    queryFn: () => apiClient.listUnavailableDemand(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const productsQuery = useQuery({
    queryKey: queryKeys.products(selectedShopId),
    queryFn: () => apiClient.listProducts(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const productNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const product of productsQuery.data ?? []) {
      map.set(product.id, product.title);
    }
    return map;
  }, [productsQuery.data]);

  const reasonOptions = useMemo(() => {
    const reasons = new Set<string>();
    for (const row of demandQuery.data ?? []) {
      reasons.add(row.reason);
    }
    return Array.from(reasons).sort((a, b) =>
      formatMismatchReason(a).localeCompare(formatMismatchReason(b)),
    );
  }, [demandQuery.data]);

  // Sprint 4 (additive): group the same raw demand logs by product/variant for
  // a recovery-oriented view. Reuses the pure builder so grouping logic lives
  // in one place. No new fetch — derives from already-loaded data.
  const lostDemandInsights = useMemo(() => {
    const rows: LostDemandRow[] = (demandQuery.data ?? []).map((log) => ({
      requested_product: productNames.get(log.product_id ?? '') ?? null,
      requested_color: log.requested_color_normalized ?? log.requested_color_raw ?? null,
      requested_size: log.requested_size_normalized ?? log.requested_size_raw ?? null,
      product_id: log.product_id ?? null,
      count: 1,
      estimated_lost_revenue: String(log.estimated_lost_revenue ?? 0),
      reason: log.reason,
    }));
    const input = { shopId: selectedShopId ?? '', lostDemand: rows, products: productsQuery.data ?? null } as Pick<
      RevenueRecoveryAggregationInput,
      'shopId' | 'lostDemand' | 'products'
    >;
    return buildLostDemandInsights(input);
  }, [demandQuery.data, productNames, productsQuery.data, selectedShopId]);

  const summary = useMemo(() => {
    const rows = demandQuery.data ?? [];
    const reasonStats = new Map<string, { count: number; revenue: number }>();
    let totalLostRevenue = 0;
    let totalQuantity = 0;
    const productIds = new Set<string>();

    for (const row of rows) {
      const existing = reasonStats.get(row.reason) ?? { count: 0, revenue: 0 };
      existing.count += 1;
      if (row.estimated_lost_revenue != null) {
        existing.revenue += row.estimated_lost_revenue;
        totalLostRevenue += row.estimated_lost_revenue;
      }
      reasonStats.set(row.reason, existing);
      totalQuantity += row.requested_quantity;
      if (row.product_id) {
        productIds.add(row.product_id);
      }
    }

    const reasonBreakdown = Array.from(reasonStats.entries())
      .map(([reason, stats]) => ({
        reason,
        count: stats.count,
        revenue: stats.revenue,
        share: rows.length > 0 ? stats.count / rows.length : 0,
      }))
      .sort((a, b) => b.count - a.count || b.revenue - a.revenue);

    return {
      totalRequests: rows.length,
      totalLostRevenue,
      totalQuantity,
      productsAffected: productIds.size,
      reasonBreakdown,
    };
  }, [demandQuery.data]);

  const filteredRows = useMemo(() => {
    let rows = demandQuery.data ?? [];

    if (reasonFilter) {
      rows = rows.filter((row) => row.reason === reasonFilter);
    }

    return filterBySearch(rows, (row) => buildSearchText(row, productNames.get(row.product_id ?? '')), search);
  }, [demandQuery.data, reasonFilter, search, productNames]);

  const pageRows = useMemo(
    () => paginateItems(filteredRows, page, PAGE_SIZE),
    [filteredRows, page],
  );

  const isLoading = demandQuery.isLoading || productsQuery.isLoading;

  const logColumns: Column<UnavailableDemandLog>[] = [
    {
      key: 'reason',
      header: 'Reason',
      render: (row) => <ReasonBadge reason={row.reason} />,
    },
    {
      key: 'product',
      header: 'Product',
      render: (row) => {
        const productName = row.product_id ? productNames.get(row.product_id) : undefined;
        if (row.product_id && productName) {
          return (
            <Link
              className="font-medium text-accent hover:underline"
              to={`/catalog/products/${row.product_id}?shopId=${selectedShopId}`}
            >
              {productName}
            </Link>
          );
        }
        if (row.product_id) {
          return (
            <span className="font-mono text-xs text-muted" title={row.product_id}>
              Unknown product
            </span>
          );
        }
        return '—';
      },
    },
    {
      key: 'color',
      header: 'Color',
      render: (row) => (
        <SlotValue raw={row.requested_color_raw} normalized={row.requested_color_normalized} />
      ),
    },
    {
      key: 'size',
      header: 'Size',
      render: (row) => (
        <SlotValue raw={row.requested_size_raw} normalized={row.requested_size_normalized} />
      ),
    },
    {
      key: 'qty',
      header: 'Qty',
      render: (row) => row.requested_quantity,
    },
    {
      key: 'lost',
      header: 'Est. lost',
      align: 'right',
      render: (row) => (
        <span className="tabular-nums">{formatMoney(row.estimated_lost_revenue ?? null)}</span>
      ),
    },
  ];

  return (
    <HubPage
      eyebrow="Insights"
      title="Unavailable demand"
      description="Every request the resolver could not fulfill — wrong variant, missing alias, or out of stock. Use this log to restock, add dictionary aliases, or fix catalog gaps."
    >
      <Card>
        <CardBody className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <Link className={ghostLinkClass} to="/catalog/attributes">
            Manage attribute aliases
          </Link>
          <span className="text-subtle" aria-hidden="true">
            ·
          </span>
          <Link className={ghostLinkClass} to="/catalog/resolver">
            Test resolver
          </Link>
          <span className="text-subtle" aria-hidden="true">
            ·
          </span>
          <Link className={ghostLinkClass} to="/analytics">
            View aggregated analytics
          </Link>
        </CardBody>
      </Card>

      {!selectedShopId ? (
        <Card>
          <CardBody>
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          </CardBody>
        </Card>
      ) : isLoading ? (
        <Card>
          <CardBody>
            <LoadingState label="Loading demand logs…" />
          </CardBody>
        </Card>
      ) : demandQuery.error ? (
        <Card>
          <CardBody>
            <p className="text-sm text-danger">
              {demandQuery.error instanceof Error
                ? demandQuery.error.message
                : 'Failed to load unavailable demand'}
            </p>
          </CardBody>
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader
              title="Summary"
              description={`${selectedShop?.name ?? 'Shop'} — missed demand captured by the variant resolver`}
            />
            <CardBody>
              {summary.totalRequests === 0 ? (
                <EmptyState title="No unavailable demand logged for this shop yet." />
              ) : (
                <div className="flex flex-col gap-6">
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <KpiCard label="Estimated lost revenue" value={formatMoney(summary.totalLostRevenue)} tone="danger" />
                    <KpiCard label="Requests" value={summary.totalRequests.toLocaleString()} />
                    <KpiCard label="Units requested" value={summary.totalQuantity.toLocaleString()} />
                    <KpiCard label="Products affected" value={summary.productsAffected.toLocaleString()} />
                  </div>

                  <p className="text-sm text-muted">
                    Revenue the shop missed when the resolver could not match a fulfillable variant. Click a reason
                    below to filter the request log.
                  </p>

                  <div>
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <p className="text-sm font-medium text-fg">Breakdown by reason</p>
                      {reasonFilter ? (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setPage(1);
                            setReasonFilter('');
                          }}
                        >
                          Clear filter
                        </Button>
                      ) : null}
                    </div>

                    <ul className="flex flex-col gap-2">
                      {summary.reasonBreakdown.map((item) => {
                        const isActive = reasonFilter === item.reason;
                        const sharePercent = Math.round(item.share * 100);
                        const tone = demandReasonTone(item.reason) as BadgeTone;

                        return (
                          <li key={item.reason}>
                            <button
                              type="button"
                              className={cn(
                                'w-full rounded-lg border px-4 py-3 text-left transition-colors',
                                isActive
                                  ? 'border-accent bg-accent-soft/30'
                                  : 'border-border bg-surface hover:bg-surface-sunken',
                              )}
                              aria-pressed={isActive}
                              onClick={() => {
                                setPage(1);
                                setReasonFilter((current) => (current === item.reason ? '' : item.reason));
                              }}
                            >
                              <span className="flex flex-wrap items-center justify-between gap-2">
                                <ReasonBadge reason={item.reason} />
                                <span className="flex flex-wrap items-center gap-3 text-sm text-muted">
                                  <span>
                                    {item.count} request{item.count === 1 ? '' : 's'}
                                  </span>
                                  <span className="tabular-nums">{formatMoney(item.revenue)}</span>
                                </span>
                              </span>
                              <span className="mt-2 block h-1.5 overflow-hidden rounded-full bg-surface-sunken" aria-hidden="true">
                                <span
                                  className={cn('block h-full rounded-full', REASON_BAR_CLASS[tone])}
                                  style={{ width: `${Math.max(sharePercent, 8)}%` }}
                                />
                              </span>
                              <span className="mt-1 block text-xs text-subtle">{sharePercent}% of requests</span>
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Request log"
              description={
                reasonFilter
                  ? `Showing ${formatMismatchReason(reasonFilter).toLowerCase()} requests only.`
                  : 'Raw customer input and normalized values captured at resolution time.'
              }
            />
            <div className="border-b border-border px-5 py-3">
              <FilterBar
                search={search}
                onSearch={(value) => {
                  setPage(1);
                  setSearch(value);
                }}
                searchPlaceholder="Attribute, product, reason…"
              >
                <Field label="Reason" className="min-w-[10rem]">
                  <Select
                    value={reasonFilter}
                    onChange={(event) => {
                      setPage(1);
                      setReasonFilter(event.target.value);
                    }}
                  >
                    <option value="">All reasons</option>
                    {reasonOptions.map((reason) => (
                      <option key={reason} value={reason}>
                        {formatMismatchReason(reason)}
                      </option>
                    ))}
                  </Select>
                </Field>
              </FilterBar>
            </div>

            {filteredRows.length === 0 ? (
              <CardBody>
                <EmptyState
                  title={
                    summary.totalRequests === 0
                      ? 'No unavailable demand logged yet. Requests appear when the variant resolver fails to match stock.'
                      : 'No requests match your filters.'
                  }
                  action={
                    summary.totalRequests === 0 ? (
                      <div className="flex flex-wrap justify-center gap-2">
                        <Link
                          className="inline-flex h-8 items-center rounded-lg px-3 text-xs font-medium text-muted hover:bg-surface-sunken hover:text-fg"
                          to="/catalog/attributes"
                        >
                          Add aliases
                        </Link>
                        <Link
                          className="inline-flex h-8 items-center rounded-lg bg-accent px-3 text-xs font-medium text-accent-fg hover:opacity-90"
                          to="/variant-resolver"
                        >
                          Run resolver test
                        </Link>
                      </div>
                    ) : (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setSearch('');
                          setReasonFilter('');
                          setPage(1);
                        }}
                      >
                        Clear filters
                      </Button>
                    )
                  }
                />
              </CardBody>
            ) : (
              <>
                <DataTable
                  columns={logColumns}
                  rows={pageRows}
                  rowKey={(row) => row.id}
                  emptyTitle="No requests match your filters."
                />
                <Pagination
                  page={page}
                  pageSize={PAGE_SIZE}
                  totalItems={filteredRows.length}
                  onPageChange={setPage}
                />
              </>
            )}
          </Card>

          {/* Sprint 4 (additive): lost demand grouped by product/variant. */}
          <LostDemandTable insights={lostDemandInsights} />
        </>
      )}
    </HubPage>
  );
}
