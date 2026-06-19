import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { filterBySearch, Pagination, paginateItems } from '../components/Pagination';
import { HubPage } from '../components/shell/HubPage';
import { Badge, Card, Field, Select } from '../components/ui';
import { DataTable, FilterBar } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { Order } from '../types/order';
import {
  ORDER_STATUS_OPTIONS,
  PAYMENT_STATUS_OPTIONS,
  SHIPPING_STATUS_OPTIONS,
  type OrderPaymentStatus,
  type OrderShippingStatus,
  type OrderStatus,
} from '../types/orderEnums';

const PAGE_SIZE = 15;

function statusTone(status: string): 'neutral' | 'success' | 'warning' | 'danger' | 'info' {
  if (['paid', 'delivered', 'shipped'].includes(status)) return 'success';
  if (['payment_pending', 'pending', 'preparing'].includes(status)) return 'warning';
  if (['failed', 'cancelled', 'expired'].includes(status)) return 'danger';
  return 'neutral';
}

export function OrdersPage() {
  const { selectedShopId } = useShop();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<OrderStatus | ''>('');
  const [paymentStatusFilter, setPaymentStatusFilter] = useState<OrderPaymentStatus | ''>('');
  const [shippingStatusFilter, setShippingStatusFilter] = useState<OrderShippingStatus | ''>('');
  const [createdFrom, setCreatedFrom] = useState('');
  const [createdTo, setCreatedTo] = useState('');

  const filters = {
    status: statusFilter || undefined,
    payment_status: paymentStatusFilter || undefined,
    shipping_status: shippingStatusFilter || undefined,
    created_from: createdFrom ? new Date(createdFrom).toISOString() : undefined,
    created_to: createdTo ? new Date(createdTo).toISOString() : undefined,
  };

  const ordersQuery = useQuery({
    queryKey: queryKeys.orders(selectedShopId, filters),
    queryFn: () => apiClient.listOrders(selectedShopId, filters),
    enabled: Boolean(selectedShopId),
  });

  const filteredOrders = useMemo(() => {
    const orders = ordersQuery.data ?? [];
    return filterBySearch(orders, (order) => `${order.customer_name} ${order.id} ${order.phone ?? ''}`, search);
  }, [ordersQuery.data, search]);

  const pageItems = useMemo(() => paginateItems(filteredOrders, page, PAGE_SIZE), [filteredOrders, page]);

  const columns: Column<Order>[] = [
    {
      key: 'order',
      header: 'Order',
      render: (order) => (
        <Link className="font-mono text-sm text-accent hover:underline" to={`/orders/${order.id}?shopId=${selectedShopId}`}>
          {order.id.slice(0, 8)}
        </Link>
      ),
    },
    { key: 'customer', header: 'Customer', render: (order) => order.customer_name },
    {
      key: 'status',
      header: 'Status',
      render: (order) => <Badge tone={statusTone(order.status)}>{order.status.replace(/_/g, ' ')}</Badge>,
    },
    {
      key: 'payment',
      header: 'Payment',
      className: 'hidden md:table-cell',
      render: (order) => <Badge tone={statusTone(order.payment_status)}>{order.payment_status}</Badge>,
    },
    {
      key: 'shipping',
      header: 'Shipping',
      className: 'hidden lg:table-cell',
      render: (order) => order.shipping_status.replace(/_/g, ' '),
    },
    {
      key: 'total',
      header: 'Total',
      align: 'right',
      render: (order) => (
        <span className="tabular-nums font-medium">
          {order.total_amount} {order.currency}
        </span>
      ),
    },
    {
      key: 'conversation',
      header: 'Chat',
      align: 'right',
      render: (order) => (
        <Link className="text-xs text-accent hover:underline" to={`/inbox/${order.conversation_id}?shopId=${selectedShopId}`}>
          View
        </Link>
      ),
    },
    {
      key: 'created',
      header: 'Created',
      className: 'hidden sm:table-cell',
      align: 'right',
      render: (order) => (
        <time className="text-xs text-subtle" dateTime={order.created_at}>
          {new Date(order.created_at).toLocaleDateString()}
        </time>
      ),
    },
  ];

  return (
    <HubPage
      eyebrow="Fulfillment"
      title="Orders"
      description="Track draft orders, payments, shipping, and linked conversations."
    >
      <Card>
        <div className="flex flex-col gap-4 border-b border-border px-5 py-4">
          <FilterBar
            search={search}
            onSearch={(value) => { setPage(1); setSearch(value); }}
            searchPlaceholder="Customer, phone, order ID…"
          />
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Field label="Status">
              <Select
                value={statusFilter}
                onChange={(event) => { setPage(1); setStatusFilter(event.target.value as OrderStatus | ''); }}
              >
                <option value="">All</option>
                {ORDER_STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>{status.replace(/_/g, ' ')}</option>
                ))}
              </Select>
            </Field>
            <Field label="Payment">
              <Select
                value={paymentStatusFilter}
                onChange={(event) => { setPage(1); setPaymentStatusFilter(event.target.value as OrderPaymentStatus | ''); }}
              >
                <option value="">All</option>
                {PAYMENT_STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>{status}</option>
                ))}
              </Select>
            </Field>
            <Field label="Shipping">
              <Select
                value={shippingStatusFilter}
                onChange={(event) => { setPage(1); setShippingStatusFilter(event.target.value as OrderShippingStatus | ''); }}
              >
                <option value="">All</option>
                {SHIPPING_STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>{status.replace(/_/g, ' ')}</option>
                ))}
              </Select>
            </Field>
            <Field label="From">
              <input
                type="date"
                value={createdFrom}
                onChange={(event) => { setPage(1); setCreatedFrom(event.target.value); }}
                className="h-9 w-full rounded-lg border border-border bg-surface px-3 text-sm text-fg focus:border-accent focus:outline-none"
              />
            </Field>
            <Field label="To">
              <input
                type="date"
                value={createdTo}
                onChange={(event) => { setPage(1); setCreatedTo(event.target.value); }}
                className="h-9 w-full rounded-lg border border-border bg-surface px-3 text-sm text-fg focus:border-accent focus:outline-none"
              />
            </Field>
          </div>
        </div>

        <DataTable
          columns={columns}
          rows={pageItems}
          rowKey={(order) => order.id}
          isLoading={ordersQuery.isLoading}
          error={ordersQuery.error instanceof Error ? ordersQuery.error.message : null}
          emptyTitle="No orders match your filters"
        />
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={filteredOrders.length} onPageChange={setPage} />
      </Card>
    </HubPage>
  );
}
