import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';

type PendingAction = 'markPaid' | 'ship' | 'cancel' | 'confirm' | null;

export function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const [searchParams] = useSearchParams();
  const { selectedShopId } = useShop();
  const shopId = searchParams.get('shopId') ?? selectedShopId;
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const [trackingCode, setTrackingCode] = useState('');
  const [trackingUrl, setTrackingUrl] = useState('');
  const [cancelReason, setCancelReason] = useState('');
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);

  const orderQuery = useQuery({
    queryKey: queryKeys.order(shopId, orderId ?? ''),
    queryFn: () => apiClient.getOrder(shopId, orderId!),
    enabled: Boolean(shopId && orderId),
  });

  const order = orderQuery.data;

  function invalidateOrder() {
    queryClient.invalidateQueries({ queryKey: queryKeys.order(shopId, orderId!) });
    queryClient.invalidateQueries({ queryKey: queryKeys.orders(shopId) });
  }

  const actionMutation = useMutation({
    mutationFn: async (action: PendingAction) => {
      if (!shopId || !orderId) {
        throw new Error('Missing order context');
      }
      if (action === 'markPaid') {
        return apiClient.markOrderPaid(shopId, orderId);
      }
      if (action === 'confirm') {
        return apiClient.confirmOrder(shopId, orderId);
      }
      if (action === 'ship') {
        return apiClient.shipOrder(shopId, orderId, {
          tracking_code: trackingCode.trim(),
          tracking_url: trackingUrl.trim() || undefined,
        });
      }
      return apiClient.cancelOrder(shopId, orderId, {
        reason: cancelReason.trim() || undefined,
      });
    },
    onSuccess: () => {
      showToast('Order updated.', 'success');
      setPendingAction(null);
      invalidateOrder();
    },
    onError: (error) => {
      showToast(error instanceof Error ? error.message : 'Action failed', 'error');
      setPendingAction(null);
    },
  });

  if (!shopId) {
    return (
      <section className="dashboard-card">
        <p className="empty-state">Select a shop to view this order.</p>
        <Link className="table-link" to="/orders">
          Back to orders
        </Link>
      </section>
    );
  }

  if (orderQuery.isLoading) {
    return <p className="loading-state">Loading order...</p>;
  }

  if (orderQuery.error || !order) {
    return (
      <section className="dashboard-card">
        <p className="form-error">
          {orderQuery.error instanceof Error ? orderQuery.error.message : 'Order not found'}
        </p>
        <Link className="table-link" to="/orders">
          Back to orders
        </Link>
      </section>
    );
  }

  const latestPayment = order.payments?.[0];
  const latestShipment = order.shipments?.[0];

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Order detail</p>
        <h1>Order {order.id.slice(0, 8)}</h1>
        <p>
          <Link className="table-link" to="/orders">
            Back to orders
          </Link>
          {' · '}
          <Link
            className="table-link"
            to={`/conversations/${order.conversation_id}?shopId=${shopId}`}
          >
            View conversation
          </Link>
        </p>

        <dl className="detail-grid">
          <div>
            <dt>Status</dt>
            <dd>{order.status}</dd>
          </div>
          <div>
            <dt>Payment</dt>
            <dd>{order.payment_status}</dd>
          </div>
          <div>
            <dt>Shipping</dt>
            <dd>{order.shipping_status}</dd>
          </div>
          <div>
            <dt>Total</dt>
            <dd>
              {order.total_amount} {order.currency}
            </dd>
          </div>
          <div>
            <dt>Customer</dt>
            <dd>{order.customer_name}</dd>
          </div>
          <div>
            <dt>Phone</dt>
            <dd>{order.phone}</dd>
          </div>
          <div>
            <dt>City</dt>
            <dd>{order.city}</dd>
          </div>
          <div>
            <dt>Address</dt>
            <dd>{order.address}</dd>
          </div>
        </dl>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Items</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Product</th>
                <th>Variant</th>
                <th>SKU</th>
                <th>Qty</th>
                <th>Unit</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {order.items.map((item) => (
                <tr key={item.id}>
                  <td>{item.product_title_snapshot}</td>
                  <td>
                    {[item.variant_color_snapshot, item.variant_size_snapshot].filter(Boolean).join(' / ') || '—'}
                  </td>
                  <td>{item.sku_snapshot}</td>
                  <td>{item.quantity}</td>
                  <td>{item.unit_price}</td>
                  <td>{item.total_price}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Payment info</h2>
        {latestPayment ? (
          <dl className="detail-grid">
            <div>
              <dt>Provider</dt>
              <dd>{latestPayment.provider}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{latestPayment.status}</dd>
            </div>
            <div>
              <dt>Reference</dt>
              <dd>{latestPayment.provider_reference ?? '—'}</dd>
            </div>
            {latestPayment.payment_url ? (
              <div>
                <dt>URL</dt>
                <dd>
                  <a href={latestPayment.payment_url} target="_blank" rel="noreferrer">
                    {latestPayment.payment_url}
                  </a>
                </dd>
              </div>
            ) : null}
          </dl>
        ) : (
          <p className="empty-state">No payment record yet.</p>
        )}
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Shipping info</h2>
        {latestShipment ? (
          <dl className="detail-grid">
            <div>
              <dt>Provider</dt>
              <dd>{latestShipment.provider}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{latestShipment.status}</dd>
            </div>
            <div>
              <dt>Tracking</dt>
              <dd>{latestShipment.tracking_code ?? '—'}</dd>
            </div>
          </dl>
        ) : (
          <p className="empty-state">Not shipped yet.</p>
        )}
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Status timeline</h2>
        <ol className="timeline-list">
          {order.timeline.map((event) => (
            <li key={`${event.status}-${event.occurred_at}`}>
              <strong>{event.label}</strong>
              <span>
                {new Date(event.occurred_at).toLocaleString()} · {event.source}
              </span>
            </li>
          ))}
        </ol>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Operator actions</h2>
        <div className="button-row">
          <button className="button button--primary" type="button" onClick={() => setPendingAction('confirm')}>
            Confirm order
          </button>
          <button className="button button--primary" type="button" onClick={() => setPendingAction('markPaid')}>
            Mark as paid
          </button>
        </div>

        <form
          className="inline-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (trackingCode.trim()) {
              setPendingAction('ship');
            }
          }}
        >
          <label className="form-field">
            <span>Tracking code</span>
            <input value={trackingCode} onChange={(event) => setTrackingCode(event.target.value)} required />
          </label>
          <label className="form-field">
            <span>Tracking URL</span>
            <input value={trackingUrl} onChange={(event) => setTrackingUrl(event.target.value)} />
          </label>
          <button className="button button--primary" type="submit" disabled={actionMutation.isPending}>
            Ship order
          </button>
        </form>

        <form
          className="inline-form"
          onSubmit={(event) => {
            event.preventDefault();
            setPendingAction('cancel');
          }}
        >
          <label className="form-field">
            <span>Cancel reason</span>
            <input value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} />
          </label>
          <button className="button button--danger" type="submit" disabled={actionMutation.isPending}>
            Cancel order
          </button>
        </form>
      </section>

      <ConfirmDialog
        open={pendingAction === 'markPaid'}
        title="Mark order as paid?"
        message="This records payment for the order outside the normal payment callback flow."
        confirmLabel="Mark paid"
        onConfirm={() => actionMutation.mutate('markPaid')}
        onCancel={() => setPendingAction(null)}
        isLoading={actionMutation.isPending}
      />
      <ConfirmDialog
        open={pendingAction === 'confirm'}
        title="Confirm order?"
        message="This reserves inventory and moves the order to waiting for payment."
        confirmLabel="Confirm"
        onConfirm={() => actionMutation.mutate('confirm')}
        onCancel={() => setPendingAction(null)}
        isLoading={actionMutation.isPending}
      />
      <ConfirmDialog
        open={pendingAction === 'ship'}
        title="Ship this order?"
        message={`Tracking code: ${trackingCode.trim() || '(none)'}`}
        confirmLabel="Ship"
        onConfirm={() => actionMutation.mutate('ship')}
        onCancel={() => setPendingAction(null)}
        isLoading={actionMutation.isPending}
      />
      <ConfirmDialog
        open={pendingAction === 'cancel'}
        title="Cancel this order?"
        message="Inventory reservations will be released. This cannot be undone."
        confirmLabel="Cancel order"
        onConfirm={() => actionMutation.mutate('cancel')}
        onCancel={() => setPendingAction(null)}
        isLoading={actionMutation.isPending}
      />
    </div>
  );
}
