import { useQuery } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';

export function PostRevenueAnalyticsPage() {
  const { selectedShopId } = useShop();

  const revenue = useQuery({
    queryKey: ['post-revenue', selectedShopId],
    queryFn: () => apiClient.getPostRevenueAnalytics(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Post attribution</p>
        <h1>Post revenue analytics</h1>
        <p>Conversations, draft orders, paid orders, revenue, conversion, and abandonment by Instagram post.</p>
        <ShopSelector />
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Performance by post</h2>
        {revenue.isLoading ? <p className="loading-state">Loading post revenue...</p> : null}
        {revenue.error ? (
          <p className="form-error">
            {revenue.error instanceof Error ? revenue.error.message : 'Failed to load analytics'}
          </p>
        ) : null}
        {!revenue.isLoading && (revenue.data?.length ?? 0) === 0 ? (
          <p className="empty-state">No post-attributed conversations yet.</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Post</th>
                  <th>Conversations</th>
                  <th>Draft orders</th>
                  <th>Paid orders</th>
                  <th>Revenue</th>
                  <th>Conversion</th>
                  <th>Abandoned</th>
                </tr>
              </thead>
              <tbody>
                {revenue.data?.map((row) => (
                  <tr key={row.instagram_post_url}>
                    <td>{row.instagram_post_url}</td>
                    <td>{row.conversations}</td>
                    <td>{row.draft_orders}</td>
                    <td>{row.paid_orders}</td>
                    <td>{row.revenue}</td>
                    <td>{(row.conversion_rate * 100).toFixed(1)}%</td>
                    <td>{(row.abandoned_rate * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
