import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';

type DatePreset = '7d' | '30d' | '90d' | 'all';

function formatDateInput(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function toIsoRangeStart(date: string): string {
  return new Date(`${date}T00:00:00`).toISOString();
}

function toIsoRangeEnd(date: string): string {
  return new Date(`${date}T23:59:59.999`).toISOString();
}

function presetRange(preset: Exclude<DatePreset, 'all'>): { start: string; end: string } {
  const end = new Date();
  const start = new Date();
  const days = preset === '7d' ? 7 : preset === '30d' ? 30 : 90;
  start.setDate(end.getDate() - (days - 1));
  return { start: formatDateInput(start), end: formatDateInput(end) };
}

function detectPreset(start: string, end: string): DatePreset | null {
  if (!start && !end) {
    return 'all';
  }
  for (const preset of ['7d', '30d', '90d'] as const) {
    const range = presetRange(preset);
    if (start === range.start && end === range.end) {
      return preset;
    }
  }
  return null;
}

const PRESET_OPTIONS: { id: DatePreset; label: string }[] = [
  { id: '7d', label: 'Last 7 days' },
  { id: '30d', label: 'Last 30 days' },
  { id: '90d', label: 'Last 90 days' },
  { id: 'all', label: 'All time' },
];

export function AnalyticsPage() {
  const { selectedShopId } = useShop();
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const startIso = startDate ? toIsoRangeStart(startDate) : undefined;
  const endIso = endDate ? toIsoRangeEnd(endDate) : undefined;
  const activePreset = useMemo(() => detectPreset(startDate, endDate), [startDate, endDate]);

  const funnel = useQuery({
    queryKey: ['analytics-funnel', selectedShopId, startIso, endIso],
    queryFn: () => apiClient.getAnalyticsFunnel(selectedShopId, startIso, endIso),
    enabled: Boolean(selectedShopId),
  });
  const posts = useQuery({
    queryKey: ['analytics-posts', selectedShopId, startIso, endIso],
    queryFn: () => apiClient.getAnalyticsPosts(selectedShopId, startIso, endIso),
    enabled: Boolean(selectedShopId),
  });
  const stock = useQuery({
    queryKey: ['analytics-stock', selectedShopId, startIso, endIso],
    queryFn: () => apiClient.getAnalyticsStockDemand(selectedShopId, startIso, endIso),
    enabled: Boolean(selectedShopId),
  });
  const unavailableDemand = useQuery({
    queryKey: ['analytics-unavailable-demand', selectedShopId, startIso, endIso],
    queryFn: () => apiClient.getAnalyticsUnavailableDemand(selectedShopId, startIso, endIso),
    enabled: Boolean(selectedShopId),
  });
  const handoff = useQuery({
    queryKey: ['analytics-handoff', selectedShopId, startIso, endIso],
    queryFn: () => apiClient.getAnalyticsHandoff(selectedShopId, startIso, endIso),
    enabled: Boolean(selectedShopId),
  });

  const isLoading =
    funnel.isLoading ||
    posts.isLoading ||
    stock.isLoading ||
    unavailableDemand.isLoading ||
    handoff.isLoading;

  function applyPreset(preset: DatePreset) {
    if (preset === 'all') {
      setStartDate('');
      setEndDate('');
      return;
    }
    const range = presetRange(preset);
    setStartDate(range.start);
    setEndDate(range.end);
  }

  function clearRange() {
    setStartDate('');
    setEndDate('');
  }

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Competitive analytics</p>
        <h1>Fashion conversion dashboard</h1>
        <p>Track funnel performance, post ROI, stock demand, and handoff reasons for the selected period.</p>
        <ShopSelector />

        <div className="analytics-toolbar">
          <div className="filter-grid analytics-toolbar__filters">
            <label className="form-field">
              <span>From</span>
              <input
                type="date"
                value={startDate}
                max={endDate || undefined}
                onChange={(event) => setStartDate(event.target.value)}
              />
            </label>
            <label className="form-field">
              <span>To</span>
              <input
                type="date"
                value={endDate}
                min={startDate || undefined}
                onChange={(event) => setEndDate(event.target.value)}
              />
            </label>
            <div className="form-field analytics-toolbar__actions">
              <span>Quick range</span>
              <div className="filter-chips analytics-toolbar__chips" role="group" aria-label="Date presets">
                {PRESET_OPTIONS.map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    className={`filter-chip${activePreset === preset.id ? ' filter-chip--active' : ''}`}
                    aria-pressed={activePreset === preset.id}
                    onClick={() => applyPreset(preset.id)}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
            {startDate || endDate ? (
              <div className="form-field analytics-toolbar__clear">
                <span aria-hidden="true">&nbsp;</span>
                <button type="button" className="button button--ghost-dark" onClick={clearRange}>
                  Clear dates
                </button>
              </div>
            ) : null}
          </div>
          {startDate || endDate ? (
            <p className="analytics-toolbar__summary">
              Showing data
              {startDate ? ` from ${startDate}` : ''}
              {endDate ? ` through ${endDate}` : ''}.
            </p>
          ) : (
            <p className="analytics-toolbar__summary">Showing all available data.</p>
          )}
        </div>
      </section>

      {!selectedShopId ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="empty-state">Select a shop to load analytics.</p>
        </section>
      ) : null}

      {selectedShopId && isLoading ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="loading-state">Loading analytics...</p>
        </section>
      ) : null}

      {funnel.data ? (
        <section className="dashboard-card dashboard-card--wide">
          <h2>Funnel cards</h2>
          <div className="stats-grid">
            <article className="stat-card">
              <p className="stat-card__label">Inbound</p>
              <p className="stat-card__value">{funnel.data.inbound_messages}</p>
            </article>
            <article className="stat-card">
              <p className="stat-card__label">Product resolved</p>
              <p className="stat-card__value">{Math.round(funnel.data.resolved_product_rate * 100)}%</p>
            </article>
            <article className="stat-card">
              <p className="stat-card__label">Variant resolved</p>
              <p className="stat-card__value">{Math.round(funnel.data.variant_resolved_rate * 100)}%</p>
            </article>
            <article className="stat-card">
              <p className="stat-card__label">Revenue</p>
              <p className="stat-card__value">{funnel.data.revenue}</p>
            </article>
          </div>
        </section>
      ) : null}

      <section className="dashboard-card dashboard-card--wide">
        <h2>Post performance</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Post</th>
                <th>Paid orders</th>
                <th>Conversion</th>
                <th>Revenue</th>
              </tr>
            </thead>
            <tbody>
              {posts.data?.map((row) => (
                <tr key={row.instagram_post_url}>
                  <td>{row.instagram_post_url}</td>
                  <td>{row.paid_orders}</td>
                  <td>{Math.round(row.conversion_rate * 100)}%</td>
                  <td>{row.revenue}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!posts.isLoading && (posts.data?.length ?? 0) === 0 ? (
            <p className="empty-state">No post performance data for this period.</p>
          ) : null}
        </div>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Stock demand signals</h2>
        <p className="analytics-toolbar__summary">
          Color and size requests that failed variant resolution during conversations.
        </p>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Value</th>
                <th>Requests</th>
              </tr>
            </thead>
            <tbody>
              {stock.data?.map((row) => (
                <tr key={`${row.type}-${row.value}`}>
                  <td>{row.type}</td>
                  <td>{row.value}</td>
                  <td>{row.requests}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {stock.error ? (
            <p className="form-error">
              {stock.error instanceof Error ? stock.error.message : 'Failed to load stock demand'}
            </p>
          ) : null}
          {!stock.isLoading && !stock.error && (stock.data?.length ?? 0) === 0 ? (
            <p className="empty-state">No stock demand signals for this period.</p>
          ) : null}
        </div>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Unavailable demand</h2>
        <p className="analytics-toolbar__summary">
          Aggregated out-of-stock or variant-mismatch requests with estimated lost revenue.
        </p>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Color</th>
                <th>Size</th>
                <th>Requests</th>
                <th>Est. lost revenue</th>
              </tr>
            </thead>
            <tbody>
              {unavailableDemand.data?.map((row) => (
                <tr key={`${row.requested_color ?? 'any'}-${row.requested_size ?? 'any'}-${row.product_id ?? 'none'}`}>
                  <td>{row.requested_color ?? '—'}</td>
                  <td>{row.requested_size ?? '—'}</td>
                  <td>{row.count}</td>
                  <td>{row.lost_revenue_estimate}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {unavailableDemand.error ? (
            <p className="form-error">
              {unavailableDemand.error instanceof Error
                ? unavailableDemand.error.message
                : 'Failed to load unavailable demand'}
            </p>
          ) : null}
          {!unavailableDemand.isLoading &&
          !unavailableDemand.error &&
          (unavailableDemand.data?.length ?? 0) === 0 ? (
            <p className="empty-state">No unavailable demand logged for this period.</p>
          ) : null}
        </div>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Handoff reasons</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Reason</th>
                <th>Count</th>
                <th>Rate</th>
              </tr>
            </thead>
            <tbody>
              {handoff.data?.map((row) => (
                <tr key={row.reason}>
                  <td>{row.reason}</td>
                  <td>{row.count}</td>
                  <td>{Math.round(row.rate * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!handoff.isLoading && (handoff.data?.length ?? 0) === 0 ? (
            <p className="empty-state">No handoff reasons recorded for this period.</p>
          ) : null}
        </div>
      </section>
    </div>
  );
}
