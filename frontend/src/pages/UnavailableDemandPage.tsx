import { useQuery } from '@tanstack/react-query';

import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';

export function UnavailableDemandPage() {
  const { selectedShop } = useShop();
  const demand = useQuery({ queryKey: ['unavailable-demand-logs', selectedShop?.id], queryFn: () => apiClient.listUnavailableDemand(selectedShop!.id), enabled: Boolean(selectedShop) });
  return <div className="page-stack"><header><p className="eyebrow">Sprint A</p><h1>Unavailable Demand</h1><p>Review unavailable color, size, variant, and stock requests captured by the backend resolver.</p></header><section className="dashboard-card"><table className="data-table"><thead><tr><th>Reason</th><th>Color</th><th>Size</th><th>Qty</th><th>Lost revenue</th></tr></thead><tbody>{demand.data?.map((row) => <tr key={row.id}><td>{row.reason}</td><td>{row.requested_color_raw} → {row.requested_color_normalized}</td><td>{row.requested_size_raw} → {row.requested_size_normalized}</td><td>{row.requested_quantity}</td><td>{row.estimated_lost_revenue ?? '—'}</td></tr>)}</tbody></table></section></div>;
}
