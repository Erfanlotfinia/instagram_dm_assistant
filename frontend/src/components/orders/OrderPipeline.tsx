import { useQuery } from '@tanstack/react-query';

import { Card } from '../ui';
import { LoadingState } from '../data';
import { useShop } from '../../contexts/ShopContext';
import { queryKeys } from '../../lib/queryClient';
import { apiClient } from '../../services/apiClient';
import type { Order } from '../../types/order';
import type { OrderStatus } from '../../types/orderEnums';

const STAGES: Array<{ label: string; statuses: OrderStatus[]; tone: string }> = [
  { label: 'Draft', statuses: ['draft', 'waiting_for_clarification', 'ready_for_confirmation', 'reserved'], tone: 'var(--c-subtle)' },
  { label: 'Awaiting payment', statuses: ['payment_pending'], tone: 'var(--c-warning)' },
  { label: 'Paid', statuses: ['paid', 'order_created'], tone: 'var(--c-success)' },
  { label: 'Shipped', statuses: [], tone: 'var(--c-info)' },
  { label: 'Cancelled / failed', statuses: ['cancelled', 'failed', 'expired'], tone: 'var(--c-danger)' },
];

export function OrderPipeline() {
  const { selectedShopId } = useShop();
  const ordersQuery = useQuery({
    queryKey: queryKeys.orders(selectedShopId, { pipeline: true }),
    queryFn: () => apiClient.listOrders(selectedShopId, {}),
    enabled: Boolean(selectedShopId),
  });

  const orders = ordersQuery.data ?? [];

  function countFor(stageIndex: number): number {
    const stage = STAGES[stageIndex];
    if (stage.label === 'Shipped') {
      return orders.filter((order: Order) => order.shipping_status === 'shipped' || order.shipping_status === 'delivered').length;
    }
    return orders.filter((order: Order) => stage.statuses.includes(order.status)).length;
  }

  if (ordersQuery.isLoading) {
    return (
      <Card>
        <LoadingState label="Loading pipeline…" />
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {STAGES.map((stage, index) => (
        <div key={stage.label} className="cc-themed rounded-[var(--radius-card)] border border-border bg-surface p-4">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: stage.tone }} />
            <p className="text-xs font-medium text-muted">{stage.label}</p>
          </div>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-fg">{countFor(index)}</p>
        </div>
      ))}
    </div>
  );
}
