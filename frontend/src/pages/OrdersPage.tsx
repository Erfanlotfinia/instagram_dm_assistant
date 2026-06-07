import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { filterBySearch, Pagination, paginateItems } from '../components/Pagination';
import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import {
  ORDER_STATUS_OPTIONS,
  PAYMENT_STATUS_OPTIONS,
  SHIPPING_STATUS_OPTIONS,
  type OrderPaymentStatus,
  type OrderShippingStatus,
  type OrderStatus,
} from '../types/orderEnums';

const PAGE_SIZE = 15;

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
    return filterBySearch(
      orders,
      (order) => `${order.customer_name} ${order.id} ${order.phone ?? ''}`,
      search,
    );
  }, [ordersQuery.data, search]);

  const pageItems = useMemo(
    () => paginateItems(filteredOrders, page, PAGE_SIZE),
    [filteredOrders, page],
  );

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Fulfillment</p>
        <h1>Orders</h1>
        <p>Track draft orders, payments, and shipping.</p>
        <ShopSelector />

        <div className="filter-grid">
          <label className="form-field">
            <span>Search</span>
            <input
              type="search"
              placeholder="Customer, phone, order ID"
              value={search}
              onChange={(event) => {
                setPage(1);
                setSearch(event.target.value);
              }}
            />
          </label>
          <label className="form-field">
            <span>Status</span>
            <select
              value={statusFilter}
              onChange={(event) => {
                setPage(1);
                setStatusFilter(event.target.value as OrderStatus | '');
              }}
            >
              <option value="">All</option>
              {ORDER_STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>Payment</span>
            <select
              value={paymentStatusFilter}
              onChange={(event) => {
                setPage(1);
                setPaymentStatusFilter(event.target.value as OrderPaymentStatus | '');
              }}
            >
              <option value="">All</option>
              {PAYMENT_STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>Shipping</span>
            <select
              value={shippingStatusFilter}
              onChange={(event) => {
                setPage(1);
                setShippingStatusFilter(event.target.value as OrderShippingStatus | '');
              }}
            >
              <option value="">All</option>
              {SHIPPING_STATUS_OPTIONS.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>From</span>
            <input
              type="date"
              value={createdFrom}
              onChange={(event) => {
                setPage(1);
                setCreatedFrom(event.target.value);
              }}
            />
          </label>
          <label className="form-field">
            <span>To</span>
            <input
              type="date"
              value={createdTo}
              onChange={(event) => {
                setPage(1);
                setCreatedTo(event.target.value);
              }}
            />
          </label>
        </div>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        {ordersQuery.isLoading ? <p className="loading-state">Loading orders...</p> : null}
        {ordersQuery.error ? (
          <p className="form-error">
            {ordersQuery.error instanceof Error ? ordersQuery.error.message : 'Failed to load orders'}
          </p>
        ) : null}

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Order</th>
                <th>Customer</th>
                <th>Status</th>
                <th>Risk</th>
                <th>Approval</th>
                <th>Payment</th>
                <th>Shipping</th>
                <th>Total</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {pageItems.map((order) => (
                <tr key={order.id}>
                  <td>
                    <Link
                      className="table-link"
                      to={`/orders/${order.id}?shopId=${selectedShopId}`}
                    >
                      {order.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td>{order.customer_name}</td>
                  <td>{order.status}</td>
                  <td>{order.risk_flags?.length ? order.risk_flags.join(', ') : '—'}</td>
                  <td>{order.approval_source ?? 'auto-approved'}</td>
                  <td>{order.payment_status}{order.payment_callback_status ? ` · ${order.payment_callback_status}` : ''}</td>
                  <td>{order.shipping_status}</td>
                  <td>
                    {order.total_amount} {order.currency}
                  </td>
                  <td>{new Date(order.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredOrders.length === 0 && !ordersQuery.isLoading ? (
            <p className="empty-state">No orders match your filters.</p>
          ) : null}
        </div>

        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          totalItems={filteredOrders.length}
          onPageChange={setPage}
        />
      </section>
    </div>
  );
}
