import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ShopSelector } from '../components/ShopSelector';
import { useAuth } from '../contexts/AuthContext';
import { useShop } from '../contexts/ShopContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';

export function DashboardPage() {
  const { user } = useAuth();
  const { selectedShopId } = useShop();

  const metricsQuery = useQuery({
    queryKey: queryKeys.dashboardMetrics(selectedShopId),
    queryFn: () => apiClient.getDashboardMetrics(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const metrics = metricsQuery.data;

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
            <h2>Conversion funnel</h2>
            <div className="funnel">
              <div className="funnel__step">
                <span className="funnel__label">Inbound messages</span>
                <strong>{metrics.conversion_funnel.inbound_messages}</strong>
              </div>
              <div className="funnel__arrow" aria-hidden="true">
                →
              </div>
              <div className="funnel__step">
                <span className="funnel__label">Product resolved</span>
                <strong>{metrics.conversion_funnel.product_resolved}</strong>
              </div>
              <div className="funnel__arrow" aria-hidden="true">
                →
              </div>
              <div className="funnel__step">
                <span className="funnel__label">Draft orders</span>
                <strong>{metrics.conversion_funnel.draft_orders}</strong>
              </div>
              <div className="funnel__arrow" aria-hidden="true">
                →
              </div>
              <div className="funnel__step">
                <span className="funnel__label">Paid orders</span>
                <strong>{metrics.conversion_funnel.paid_orders}</strong>
              </div>
            </div>
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>Revenue recovery & upsell</h2>
            <div className="stats-grid">
              <article className="stat-card">
                <p className="stat-card__label">Abandoned orders</p>
                <p className="stat-card__value">{metrics.abandoned_orders}</p>
              </article>
              <article className="stat-card">
                <p className="stat-card__label">Recovered orders</p>
                <p className="stat-card__value">{metrics.recovered_orders}</p>
              </article>
              <article className="stat-card">
                <p className="stat-card__label">Recovered revenue</p>
                <p className="stat-card__value">{metrics.recovered_revenue}</p>
              </article>
              <article className="stat-card">
                <p className="stat-card__label">Upsell suggestions</p>
                <p className="stat-card__value">{metrics.upsell_suggestions}</p>
              </article>
              <article className="stat-card">
                <p className="stat-card__label">Upsell accepted</p>
                <p className="stat-card__value">{metrics.upsell_accepted}</p>
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
