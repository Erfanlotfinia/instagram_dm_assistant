import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { filterBySearch, Pagination, paginateItems } from '../components/Pagination';
import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { queryKeys } from '../lib/queryClient';
import { demandReasonTone, formatMismatchReason } from '../lib/variantResolver';
import { apiClient } from '../services/apiClient';
import type { UnavailableDemandLog } from '../types/fashion';

const PAGE_SIZE = 12;

type ReasonTone = 'success' | 'warning' | 'danger' | 'neutral';

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
  const tone = demandReasonTone(reason) as ReasonTone;
  return (
    <span className={`order-status-badge order-status-badge--${tone}`}>
      {formatMismatchReason(reason)}
    </span>
  );
}

function SlotValue({
  raw,
  normalized,
}: {
  raw?: string | null;
  normalized?: string | null;
}) {
  if (!raw && !normalized) {
    return <span className="demand-slot demand-slot--empty">—</span>;
  }

  if (!raw || raw === normalized) {
    return <span className="demand-slot__normalized">{normalized ?? raw}</span>;
  }

  return (
    <span className="demand-slot">
      <span className="demand-slot__raw">{raw}</span>
      <span className="demand-slot__arrow" aria-hidden="true">
        →
      </span>
      <span className="demand-slot__normalized">{normalized ?? '?'}</span>
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

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Insights</p>
        <h1>Unavailable demand</h1>
        <p>
          Every request the resolver could not fulfill — wrong variant, missing alias, or out of
          stock. Use this log to restock, add dictionary aliases, or fix catalog gaps.
        </p>
        <ShopSelector />

        <div className="demand-actions">
          <Link className="table-link" to="/fashion-dictionary">
            Manage color &amp; size aliases
          </Link>
          <span className="demand-actions__sep" aria-hidden="true">
            ·
          </span>
          <Link className="table-link" to="/variant-resolver">
            Test resolver
          </Link>
          <span className="demand-actions__sep" aria-hidden="true">
            ·
          </span>
          <Link className="table-link" to="/analytics">
            View aggregated analytics
          </Link>
        </div>
      </section>

      {!selectedShopId ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="empty-state">Select a shop to review unavailable demand.</p>
        </section>
      ) : isLoading ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="loading-state">Loading demand logs…</p>
        </section>
      ) : demandQuery.error ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="form-error">
            {demandQuery.error instanceof Error
              ? demandQuery.error.message
              : 'Failed to load unavailable demand'}
          </p>
        </section>
      ) : (
        <>
          <section className="dashboard-card dashboard-card--wide demand-summary-card">
            <div className="section-header section-header--stacked">
              <div>
                <h2>Summary</h2>
                <p className="dashboard-card__subtitle">
                  {selectedShop?.name ?? 'Shop'} — missed demand captured by the variant resolver
                </p>
              </div>
            </div>

            {summary.totalRequests === 0 ? (
              <p className="empty-state">No unavailable demand logged for this shop yet.</p>
            ) : (
              <div className="demand-summary">
                <article className="demand-summary-hero">
                  <div className="demand-summary-hero__top">
                    <div>
                      <p className="demand-summary-hero__label">Estimated lost revenue</p>
                      <p className="demand-summary-hero__value">{formatMoney(summary.totalLostRevenue)}</p>
                    </div>
                    <div className="demand-summary-pills" aria-label="Demand totals">
                      <span className="demand-summary-pill">
                        <strong>{summary.totalRequests}</strong> requests
                      </span>
                      <span className="demand-summary-pill">
                        <strong>{summary.totalQuantity}</strong> units
                      </span>
                      <span className="demand-summary-pill">
                        <strong>{summary.productsAffected}</strong> products
                      </span>
                    </div>
                  </div>
                  <p className="demand-summary-hero__lead">
                    Revenue the shop missed when the resolver could not match a fulfillable variant.
                    Click a reason below to filter the request log.
                  </p>
                </article>

                <div className="demand-summary-reasons">
                  <div className="demand-summary-reasons__header">
                    <p className="demand-summary-reasons__title">Breakdown by reason</p>
                    {reasonFilter ? (
                      <button
                        className="demand-summary-reasons__clear"
                        type="button"
                        onClick={() => {
                          setPage(1);
                          setReasonFilter('');
                        }}
                      >
                        Clear filter
                      </button>
                    ) : null}
                  </div>

                  <ul className="demand-reason-list">
                    {summary.reasonBreakdown.map((item) => {
                      const isActive = reasonFilter === item.reason;
                      const sharePercent = Math.round(item.share * 100);

                      return (
                        <li key={item.reason}>
                          <button
                            type="button"
                            className={`demand-reason-row${isActive ? ' demand-reason-row--active' : ''}`}
                            aria-pressed={isActive}
                            onClick={() => {
                              setPage(1);
                              setReasonFilter((current) =>
                                current === item.reason ? '' : item.reason,
                              );
                            }}
                          >
                            <span className="demand-reason-row__top">
                              <ReasonBadge reason={item.reason} />
                              <span className="demand-reason-row__stats">
                                <span className="demand-reason-row__count">
                                  {item.count} request{item.count === 1 ? '' : 's'}
                                </span>
                                <span className="demand-reason-row__revenue">
                                  {formatMoney(item.revenue)}
                                </span>
                              </span>
                            </span>
                            <span className="demand-reason-row__bar" aria-hidden="true">
                              <span
                                className={`demand-reason-row__fill demand-reason-row__fill--${demandReasonTone(item.reason)}`}
                                style={{ width: `${Math.max(sharePercent, 8)}%` }}
                              />
                            </span>
                            <span className="demand-reason-row__share">{sharePercent}% of requests</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              </div>
            )}
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <div className="section-header section-header--stacked">
              <div>
                <h2>Request log</h2>
                <p className="dashboard-card__subtitle">
                  {reasonFilter
                    ? `Showing ${formatMismatchReason(reasonFilter).toLowerCase()} requests only.`
                    : 'Raw customer input and normalized values captured at resolution time.'}
                </p>
              </div>
            </div>

            <div className="filter-grid demand-filters">
              <label className="form-field form-field--wide">
                <span>Search</span>
                <input
                  type="search"
                  placeholder="Color, size, product, reason…"
                  value={search}
                  onChange={(event) => {
                    setPage(1);
                    setSearch(event.target.value);
                  }}
                />
              </label>
              <label className="form-field">
                <span>Reason</span>
                <select
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
                </select>
              </label>
            </div>

            {filteredRows.length === 0 ? (
              <div className="demand-empty">
                <p className="empty-state">
                  {summary.totalRequests === 0
                    ? 'No unavailable demand logged yet. Requests appear when the variant resolver fails to match stock.'
                    : 'No requests match your filters.'}
                </p>
                {summary.totalRequests === 0 ? (
                  <div className="button-row">
                    <Link className="button button--ghost-dark" to="/fashion-dictionary">
                      Add aliases
                    </Link>
                    <Link className="button button--primary" to="/variant-resolver">
                      Run resolver test
                    </Link>
                  </div>
                ) : (
                  <button
                    className="button button--ghost-dark"
                    type="button"
                    onClick={() => {
                      setSearch('');
                      setReasonFilter('');
                      setPage(1);
                    }}
                  >
                    Clear filters
                  </button>
                )}
              </div>
            ) : (
              <>
                <div className="table-wrap">
                  <table className="data-table demand-table">
                    <thead>
                      <tr>
                        <th>Reason</th>
                        <th>Product</th>
                        <th>Color</th>
                        <th>Size</th>
                        <th>Qty</th>
                        <th>Est. lost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pageRows.map((row) => {
                        const productName = row.product_id
                          ? productNames.get(row.product_id)
                          : undefined;

                        return (
                          <tr key={row.id}>
                            <td>
                              <ReasonBadge reason={row.reason} />
                            </td>
                            <td>
                              {row.product_id && productName ? (
                                <Link
                                  className="table-link"
                                  to={`/products/${row.product_id}?shopId=${selectedShopId}`}
                                >
                                  {productName}
                                </Link>
                              ) : row.product_id ? (
                                <span className="demand-product-id" title={row.product_id}>
                                  Unknown product
                                </span>
                              ) : (
                                '—'
                              )}
                            </td>
                            <td>
                              <SlotValue
                                raw={row.requested_color_raw}
                                normalized={row.requested_color_normalized}
                              />
                            </td>
                            <td>
                              <SlotValue
                                raw={row.requested_size_raw}
                                normalized={row.requested_size_normalized}
                              />
                            </td>
                            <td>{row.requested_quantity}</td>
                            <td className="demand-table__money">
                              {formatMoney(row.estimated_lost_revenue ?? null)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <Pagination
                  page={page}
                  pageSize={PAGE_SIZE}
                  totalItems={filteredRows.length}
                  onPageChange={setPage}
                />
              </>
            )}
          </section>
        </>
      )}
    </div>
  );
}
