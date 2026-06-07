import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';

export function AnalyticsPage() {
  const { selectedShopId } = useShop();
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const funnel = useQuery({ queryKey: ['analytics-funnel', selectedShopId, start, end], queryFn: () => apiClient.getAnalyticsFunnel(selectedShopId, start || undefined, end || undefined), enabled: Boolean(selectedShopId) });
  const posts = useQuery({ queryKey: ['analytics-posts', selectedShopId, start, end], queryFn: () => apiClient.getAnalyticsPosts(selectedShopId, start || undefined, end || undefined), enabled: Boolean(selectedShopId) });
  const stock = useQuery({ queryKey: ['analytics-stock', selectedShopId, start, end], queryFn: () => apiClient.getAnalyticsStockDemand(selectedShopId, start || undefined, end || undefined), enabled: Boolean(selectedShopId) });
  const handoff = useQuery({ queryKey: ['analytics-handoff', selectedShopId, start, end], queryFn: () => apiClient.getAnalyticsHandoff(selectedShopId, start || undefined, end || undefined), enabled: Boolean(selectedShopId) });
  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide"><p className="dashboard-card__eyebrow">Competitive analytics</p><h1>Fashion conversion dashboard</h1><ShopSelector />
        <div className="form-grid"><label>Start<input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} /></label><label>End<input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} /></label></div>
      </section>
      {funnel.data ? <section className="dashboard-card dashboard-card--wide"><h2>Funnel cards</h2><div className="stats-grid">
        <article className="stat-card"><p className="stat-card__label">Inbound</p><p className="stat-card__value">{funnel.data.inbound_messages}</p></article>
        <article className="stat-card"><p className="stat-card__label">Product resolved</p><p className="stat-card__value">{Math.round(funnel.data.resolved_product_rate * 100)}%</p></article>
        <article className="stat-card"><p className="stat-card__label">Variant resolved</p><p className="stat-card__value">{Math.round(funnel.data.variant_resolved_rate * 100)}%</p></article>
        <article className="stat-card"><p className="stat-card__label">Revenue</p><p className="stat-card__value">{funnel.data.revenue}</p></article>
      </div></section> : null}
      <section className="dashboard-card dashboard-card--wide"><h2>Post performance</h2><table className="data-table"><tbody>{posts.data?.map((row) => <tr key={row.instagram_post_url}><td>{row.instagram_post_url}</td><td>{row.paid_orders} paid</td><td>{Math.round(row.conversion_rate * 100)}%</td><td>{row.revenue}</td></tr>)}</tbody></table></section>
      <section className="dashboard-card dashboard-card--wide"><h2>Unavailable demand</h2><table className="data-table"><tbody>{stock.data?.map((row) => <tr key={`${row.type}-${row.value}`}><td>{row.type}</td><td>{row.value}</td><td>{row.requests}</td></tr>)}</tbody></table></section>
      <section className="dashboard-card dashboard-card--wide"><h2>Handoff reasons</h2><table className="data-table"><tbody>{handoff.data?.map((row) => <tr key={row.reason}><td>{row.reason}</td><td>{row.count}</td><td>{Math.round(row.rate * 100)}%</td></tr>)}</tbody></table></section>
    </div>
  );
}
