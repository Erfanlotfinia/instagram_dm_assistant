import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ShopSelector } from '../components/ShopSelector';
import { useAuth } from '../contexts/AuthContext';
import { useShop } from '../contexts/ShopContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { ConversionFunnelMetrics } from '../types/dashboard';

function formatMoney(value: string): string {
  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return value;
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount);
}

function buildFunnelSteps(funnel: ConversionFunnelMetrics) {
  return [
    {
      key: 'inbound',
      label: 'Inbound messages',
      description: 'Customers who DMed your shop',
      value: funnel.inbound_messages,
    },
    {
      key: 'resolved',
      label: 'Product resolved',
      description: 'We identified what they want to buy',
      value: funnel.product_resolved,
    },
    {
      key: 'draft',
      label: 'Draft orders',
      description: 'Orders created, not yet paid',
      value: funnel.draft_orders,
    },
    {
      key: 'paid',
      label: 'Paid orders',
      description: 'Checkout completed successfully',
      value: funnel.paid_orders,
    },
  ];
}

function funnelDropOff(current: number, previous: number): number {
  return Math.max(previous - current, 0);
}

export function DashboardPage() {
  const { user } = useAuth();
  const { selectedShopId } = useShop();

  const metricsQuery = useQuery({
    queryKey: queryKeys.dashboardMetrics(selectedShopId),
    queryFn: () => apiClient.getDashboardMetrics(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const metrics = metricsQuery.data;
  const funnelSteps = metrics ? buildFunnelSteps(metrics.conversion_funnel) : [];
  const inboundCount = metrics?.conversion_funnel.inbound_messages ?? 0;
  const paidCount = metrics?.conversion_funnel.paid_orders ?? 0;
  const messageToPaidRate =
    metrics && inboundCount > 0 ? Math.round((paidCount / inboundCount) * 100) : 0;
  const upsellAcceptanceRate =
    metrics && metrics.upsell_suggestions > 0
      ? Math.round((metrics.upsell_accepted / metrics.upsell_suggestions) * 100)
      : null;

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Operations</p>
        <h1>Welcome back, {user?.full_name}</h1>
        <p>Daily snapshot for Instagram DM ordering across your selected shop.</p>
        <ShopSelector />
      </section>

      {metricsQuery.isLoading ? <p className="loading-state">Loading dashboard metrics...</p> : null}
      {metricsQuery.error ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="form-error">
            {metricsQuery.error instanceof Error ? metricsQuery.error.message : 'Failed to load metrics'}
          </p>
        </section>
      ) : null}

      {metrics ? (
        <>
          <section className="dashboard-card dashboard-card--wide">
            <h2>Today at a glance</h2>
            <div className="stats-grid">
              <article className="stat-card">
                <p className="stat-card__label">Today&apos;s orders</p>
                <p className="stat-card__value">{metrics.today_orders}</p>
              </article>
              <article className="stat-card">
                <p className="stat-card__label">Paid orders</p>
                <p className="stat-card__value">{metrics.paid_orders}</p>
              </article>
              <article className="stat-card">
                <p className="stat-card__label">Waiting for payment</p>
                <p className="stat-card__value">{metrics.waiting_for_payment}</p>
              </article>
              <article className="stat-card stat-card--warning">
                <p className="stat-card__label">Handoff conversations</p>
                <p className="stat-card__value">{metrics.handoff_conversations}</p>
              </article>
            </div>
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <div className="section-header section-header--stacked">
              <div>
                <h2>Conversion funnel</h2>
                <p className="dashboard-card__subtitle">
                  {inboundCount === 0
                    ? 'No inbound messages yet — funnel metrics appear once customers start DMing.'
                    : paidCount === 0
                      ? `${inboundCount} message${inboundCount === 1 ? '' : 's'} received, none converted to a paid order yet.`
                      : `${paidCount} of ${inboundCount} message${inboundCount === 1 ? '' : 's'} became a paid order (${messageToPaidRate}% conversion).`}
                </p>
              </div>
            </div>

            {inboundCount === 0 ? (
              <p className="empty-state funnel-empty">Start receiving DMs to see how customers move through your funnel.</p>
            ) : (
              <div className="funnel-flow" role="list" aria-label="Conversion funnel">
                {funnelSteps.map((step, index) => {
                  const previousStep = index > 0 ? funnelSteps[index - 1] : null;
                  const lostCount =
                    previousStep !== null ? funnelDropOff(step.value, previousStep.value) : 0;
                  const showConnectorLabel =
                    previousStep !== null && previousStep.value > 0;

                  return (
                    <div className="funnel-flow__segment" role="listitem" key={step.key}>
                      {index > 0 ? (
                        <div className="funnel-connector" aria-hidden="true">
                          <span className="funnel-connector__line" />
                          {showConnectorLabel && previousStep ? (
                            <span className="funnel-connector__badge">
                              {step.value} of {previousStep.value} continued
                              {lostCount > 0 ? ` · ${lostCount} dropped off` : ''}
                            </span>
                          ) : (
                            <span className="funnel-connector__badge funnel-connector__badge--muted">—</span>
                          )}
                        </div>
                      ) : null}

                      <article className={`funnel-stage funnel-stage--${step.key}`}>
                        <p className="funnel-stage__count">{step.value}</p>
                        <p className="funnel-stage__label">{step.label}</p>
                        <p className="funnel-stage__desc">{step.description}</p>
                        {index === funnelSteps.length - 1 && inboundCount > 0 ? (
                          <p className="funnel-stage__result">
                            {messageToPaidRate}% of all messages
                          </p>
                        ) : null}
                      </article>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>Revenue recovery & upsell</h2>
            <p className="dashboard-card__subtitle">
              Follow-ups on abandoned checkouts and add-on offer performance.
            </p>
            <div className="stats-grid stats-grid--recovery">
              <article className="stat-card stat-card--warning">
                <p className="stat-card__label">Abandoned orders</p>
                <p className="stat-card__value">{metrics.abandoned_orders}</p>
                <p className="stat-card__hint">Expired or waiting for payment</p>
              </article>
              <article className="stat-card stat-card--success">
                <p className="stat-card__label">Recovered orders</p>
                <p className="stat-card__value">{metrics.recovered_orders}</p>
                <p className="stat-card__hint">Paid after recovery outreach</p>
              </article>
              <article className="stat-card stat-card--success">
                <p className="stat-card__label">Recovered revenue</p>
                <p className="stat-card__value">{formatMoney(metrics.recovered_revenue)}</p>
                <p className="stat-card__hint">From recovered orders</p>
              </article>
              <article className="stat-card stat-card--accent">
                <p className="stat-card__label">Upsell suggestions</p>
                <p className="stat-card__value">{metrics.upsell_suggestions}</p>
                <p className="stat-card__hint">Active add-on offers sent</p>
              </article>
              <article className="stat-card stat-card--accent">
                <p className="stat-card__label">Upsell accepted</p>
                <p className="stat-card__value">{metrics.upsell_accepted}</p>
                <p className="stat-card__hint">
                  {upsellAcceptanceRate === null ? 'No suggestions yet' : `${upsellAcceptanceRate}% acceptance rate`}
                </p>
              </article>
            </div>
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>Top selling posts</h2>
            {metrics.top_selling_posts.length === 0 ? (
              <p className="empty-state">No post-attributed paid orders yet.</p>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Post</th>
                      <th>Paid orders</th>
                      <th>Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.top_selling_posts.map((post) => (
                      <tr key={post.instagram_post_url}>
                        <td>{post.instagram_post_url}</td>
                        <td>{post.paid_orders}</td>
                        <td>{post.revenue}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>Top lost-demand variants</h2>
            {metrics.top_lost_demand_variants.length === 0 ? (
              <p className="empty-state">No unavailable demand logged yet.</p>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Color</th>
                      <th>Size</th>
                      <th>Requests</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.top_lost_demand_variants.map((row, index) => (
                      <tr key={`${row.product_id}-${index}`}>
                        <td>{row.requested_color ?? '—'}</td>
                        <td>{row.requested_size ?? '—'}</td>
                        <td>{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <div className="section-header">
              <h2>Low stock variants</h2>
              <Link className="table-link" to="/products">
                View products
              </Link>
            </div>
            {metrics.low_stock_variants.length === 0 ? (
              <p className="empty-state">All tracked variants are above the low-stock threshold.</p>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>SKU</th>
                      <th>Variant</th>
                      <th>Available</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.low_stock_variants.map((variant) => (
                      <tr key={variant.variant_id} className="row-warning">
                        <td>
                          <Link className="table-link" to={`/products/${variant.product_id}`}>
                            {variant.product_title}
                          </Link>
                        </td>
                        <td>{variant.sku}</td>
                        <td>
                          {[variant.color, variant.size].filter(Boolean).join(' / ') || '—'}
                        </td>
                        <td>{variant.available_stock}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
