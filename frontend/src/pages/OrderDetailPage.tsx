import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { OrderTimelineTab } from '../components/orders/OrderTimelineTab';
import { PilotModeBadge } from '../components/orders/PilotModeBadge';
import { ReservationStatusChip } from '../components/orders/ReservationStatusChip';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { Payment, Shipment } from '../types/order';
import type { PaymentRecordStatus, ShipmentStatus } from '../types/orderEnums';

type PendingAction = 'markPaid' | 'ship' | 'cancel' | 'confirm' | null;

type StatusTone = 'success' | 'warning' | 'danger' | 'neutral';

const PROVIDER_LABELS: Record<string, string> = {
  mock: 'Mock gateway',
  manual: 'Manual entry',
  zarinpal: 'Zarinpal',
  nextpay: 'NextPay',
  idpay: 'IDPay',
  post: 'Iran Post',
  tipax: 'Tipax',
  chapar: 'Chapar',
  other: 'Other carrier',
};

const PAYMENT_STATUS_LABELS: Record<PaymentRecordStatus, string> = {
  created: 'Created',
  pending: 'Awaiting payment',
  paid: 'Paid',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

const SHIPMENT_STATUS_LABELS: Record<ShipmentStatus, string> = {
  pending: 'Pending',
  preparing: 'Preparing',
  shipped: 'Shipped',
  delivered: 'Delivered',
  failed: 'Failed',
};

function humanize(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

function providerLabel(provider: string): string {
  return PROVIDER_LABELS[provider] ?? humanize(provider);
}

function formatDateTime(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  return new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function paymentStatusTone(status: PaymentRecordStatus): StatusTone {
  if (status === 'paid') {
    return 'success';
  }
  if (status === 'pending' || status === 'created') {
    return 'warning';
  }
  if (status === 'failed' || status === 'cancelled') {
    return 'danger';
  }
  return 'neutral';
}

function shipmentStatusTone(status: ShipmentStatus): StatusTone {
  if (status === 'delivered' || status === 'shipped') {
    return 'success';
  }
  if (status === 'preparing' || status === 'pending') {
    return 'warning';
  }
  if (status === 'failed') {
    return 'danger';
  }
  return 'neutral';
}

function StatusBadge({ label, tone }: { label: string; tone: StatusTone }) {
  return <span className={`order-status-badge order-status-badge--${tone}`}>{label}</span>;
}

function FulfillmentField({
  label,
  value,
  mono,
}: {
  label: string;
  value: ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="order-fulfillment-field">
      <span className="order-fulfillment-field__label">{label}</span>
      <span className={mono ? 'order-fulfillment-field__value order-fulfillment-field__value--mono' : 'order-fulfillment-field__value'}>
        {value}
      </span>
    </div>
  );
}

function PaymentPanel({ payment }: { payment: Payment | undefined }) {
  if (!payment) {
    return (
      <article className="order-fulfillment-card order-fulfillment-card--empty">
        <div className="order-fulfillment-card__header">
          <h3>Payment</h3>
          <StatusBadge label="No record" tone="neutral" />
        </div>
        <p className="order-fulfillment-card__empty">
          No payment has been initiated for this order yet.
        </p>
      </article>
    );
  }

  const recordedAt = formatDateTime(payment.updated_at ?? payment.created_at);

  return (
    <article className="order-fulfillment-card order-fulfillment-card--payment">
      <div className="order-fulfillment-card__header">
        <div>
          <h3>Payment</h3>
          <p className="order-fulfillment-card__subtitle">{providerLabel(payment.provider)}</p>
        </div>
        <StatusBadge label={PAYMENT_STATUS_LABELS[payment.status]} tone={paymentStatusTone(payment.status)} />
      </div>

      <div className="order-fulfillment-card__body">
        {payment.provider_reference ? (
          <FulfillmentField label="Reference" value={payment.provider_reference} mono />
        ) : null}
        {recordedAt ? <FulfillmentField label="Last updated" value={recordedAt} /> : null}
      </div>

      {payment.payment_url ? (
        <div className="order-fulfillment-card__actions">
          <a
            className="button button--ghost-dark order-fulfillment-card__link"
            href={payment.payment_url}
            target="_blank"
            rel="noreferrer"
          >
            Open payment page
          </a>
          <span className="order-fulfillment-card__url-hint" title={payment.payment_url}>
            Demo checkout link
          </span>
        </div>
      ) : null}
    </article>
  );
}

function OperatorActionRow({
  title,
  description,
  buttonLabel,
  buttonClassName = 'button button--ghost-dark',
  disabled,
  unavailableReason,
  completed = false,
  completedLabel = 'Done',
  onClick,
}: {
  title: string;
  description: string;
  buttonLabel: string;
  buttonClassName?: string;
  disabled: boolean;
  unavailableReason?: string;
  completed?: boolean;
  completedLabel?: string;
  onClick: () => void;
}) {
  if (completed) {
    return (
      <li className="order-operator-action-item order-operator-action-item--complete">
        <div className="order-operator-action-item__content">
          <strong>{title}</strong>
          <p>{description}</p>
        </div>
        <span className="order-operator-action-item__done">{completedLabel}</span>
      </li>
    );
  }

  return (
    <li className={`order-operator-action-item${disabled ? ' order-operator-action-item--disabled' : ''}`}>
      <div className="order-operator-action-item__content">
        <strong>{title}</strong>
        <p>{disabled && unavailableReason ? unavailableReason : description}</p>
      </div>
      <button className={buttonClassName} type="button" onClick={onClick} disabled={disabled}>
        {buttonLabel}
      </button>
    </li>
  );
}

function OperatorActionsPanel({
  order,
  trackingCode,
  trackingUrl,
  cancelReason,
  isPending,
  onTrackingCodeChange,
  onTrackingUrlChange,
  onCancelReasonChange,
  onConfirm,
  onMarkPaid,
  onShipSubmit,
  onCancelSubmit,
}: {
  order: {
    status: string;
    payment_status: string;
  };
  trackingCode: string;
  trackingUrl: string;
  cancelReason: string;
  isPending: boolean;
  onTrackingCodeChange: (value: string) => void;
  onTrackingUrlChange: (value: string) => void;
  onCancelReasonChange: (value: string) => void;
  onConfirm: () => void;
  onMarkPaid: () => void;
  onShipSubmit: (event: FormEvent) => void;
  onCancelSubmit: (event: FormEvent) => void;
}) {
  const canConfirm =
    order.status === 'draft' ||
    order.status === 'waiting_for_clarification' ||
    order.status === 'ready_for_confirmation' ||
    order.status === 'reserved';
  const canMarkPaid = order.payment_status !== 'paid';
  const confirmComplete =
    !canConfirm &&
    order.status !== 'cancelled' &&
    order.status !== 'expired' &&
    order.status !== 'draft';
  const markPaidComplete = order.payment_status === 'paid';
  const canShip = order.status === 'paid' || order.status === 'order_created';
  const canCancel =
    order.status !== 'cancelled' &&
    order.status !== 'expired' &&
    order.status !== 'order_created';

  return (
    <div className="order-operator-actions">
      <article className="order-operator-card order-operator-card--payment">
        <header className="order-operator-card__top">
          <div className="order-operator-card__title-block">
            <span className="order-operator-card__step">Step 1</span>
            <h3>Payment &amp; confirmation</h3>
          </div>
          <div className="order-operator-status-row" aria-label="Current order state">
            <StatusBadge label={humanize(order.status)} tone="neutral" />
            <StatusBadge
              label={`Payment: ${humanize(order.payment_status)}`}
              tone={
                order.payment_status === 'paid'
                  ? 'success'
                  : order.payment_status === 'pending'
                    ? 'warning'
                    : 'neutral'
              }
            />
          </div>
        </header>

        <ul className="order-operator-action-list">
          <OperatorActionRow
            title="Confirm order"
            description="Reserve inventory and send the customer to checkout."
            unavailableReason="Available when the order is draft or awaiting confirmation."
            buttonLabel="Confirm"
            buttonClassName="button button--primary"
            disabled={isPending || !canConfirm}
            completed={confirmComplete}
            completedLabel="Confirmed"
            onClick={onConfirm}
          />
          <OperatorActionRow
            title="Mark as paid"
            description="Record a manual payment when checkout happened offline."
            unavailableReason="This order is already marked as paid."
            buttonLabel="Mark paid"
            disabled={isPending || !canMarkPaid}
            completed={markPaidComplete}
            completedLabel="Paid"
            onClick={onMarkPaid}
          />
        </ul>
      </article>

      <article className="order-operator-card order-operator-card--ship">
        <header className="order-operator-card__top">
          <div className="order-operator-card__title-block">
            <span className="order-operator-card__step">Step 2</span>
            <h3>Ship order</h3>
          </div>
        </header>
        <p className="order-operator-card__lead">
          Add tracking details and notify the customer when the package leaves.
        </p>
        <form className="order-operator-form" onSubmit={onShipSubmit}>
          <label className="form-field">
            <span>Tracking code</span>
            <input
              value={trackingCode}
              onChange={(event) => onTrackingCodeChange(event.target.value)}
              placeholder="e.g. DEMO-123456"
              disabled={isPending || !canShip}
              required
            />
          </label>
          <label className="form-field">
            <span>Tracking URL</span>
            <input
              value={trackingUrl}
              onChange={(event) => onTrackingUrlChange(event.target.value)}
              placeholder="https://tracking.example.com/..."
              disabled={isPending || !canShip}
            />
          </label>
          <button
            className="button button--primary"
            type="submit"
            disabled={isPending || !canShip || !trackingCode.trim()}
          >
            {isPending ? 'Saving…' : 'Ship order'}
          </button>
        </form>
        {!canShip ? (
          <p className="order-operator-card__footnote order-operator-card__footnote--muted">
            Shipping is available after the order is paid.
          </p>
        ) : null}
      </article>

      <article className="order-operator-card order-operator-card--danger">
        <header className="order-operator-card__top">
          <div className="order-operator-card__title-block">
            <span className="order-operator-card__step order-operator-card__step--danger">Danger zone</span>
            <h3>Cancel order</h3>
          </div>
        </header>
        <p className="order-operator-card__lead order-operator-card__lead--danger">
          Releases inventory reservations and closes the order permanently.
        </p>
        <form className="order-operator-form" onSubmit={onCancelSubmit}>
          <label className="form-field form-field--wide">
            <span>Cancel reason</span>
            <input
              value={cancelReason}
              onChange={(event) => onCancelReasonChange(event.target.value)}
              placeholder="Optional note for the audit trail"
              disabled={isPending || !canCancel}
            />
          </label>
          <button className="button button--danger" type="submit" disabled={isPending || !canCancel}>
            Cancel order
          </button>
        </form>
      </article>
    </div>
  );
}

function ShippingPanel({ shipment }: { shipment: Shipment | undefined }) {
  if (!shipment) {
    return (
      <article className="order-fulfillment-card order-fulfillment-card--empty">
        <div className="order-fulfillment-card__header">
          <h3>Shipping</h3>
          <StatusBadge label="Not started" tone="neutral" />
        </div>
        <p className="order-fulfillment-card__empty">
          Shipment has not been created yet. Use operator actions below to ship this order.
        </p>
      </article>
    );
  }

  const shippedAt = formatDateTime(shipment.shipped_at ?? shipment.created_at);

  return (
    <article className="order-fulfillment-card order-fulfillment-card--shipping">
      <div className="order-fulfillment-card__header">
        <div>
          <h3>Shipping</h3>
          <p className="order-fulfillment-card__subtitle">{providerLabel(shipment.provider)}</p>
        </div>
        <StatusBadge label={SHIPMENT_STATUS_LABELS[shipment.status]} tone={shipmentStatusTone(shipment.status)} />
      </div>

      <div className="order-fulfillment-card__body">
        <FulfillmentField label="Tracking code" value={shipment.tracking_code ?? '—'} mono />
        {shippedAt ? <FulfillmentField label="Shipped at" value={shippedAt} /> : null}
      </div>

      {shipment.tracking_url ? (
        <div className="order-fulfillment-card__actions">
          <a
            className="button button--ghost-dark order-fulfillment-card__link"
            href={shipment.tracking_url}
            target="_blank"
            rel="noreferrer"
          >
            Track shipment
          </a>
        </div>
      ) : null}
    </article>
  );
}

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

  const correctnessQuery = useQuery({
    queryKey: queryKeys.orderCorrectness(orderId ?? ''),
    queryFn: () => apiClient.getOrderCorrectness(orderId!),
    enabled: Boolean(orderId),
  });

  const order = orderQuery.data;
  const correctness = correctnessQuery.data;
  const latestShipment = order?.shipments?.[0];

  useEffect(() => {
    if (latestShipment?.tracking_code) {
      setTrackingCode((current) => current || latestShipment.tracking_code || '');
    }
    if (latestShipment?.tracking_url) {
      setTrackingUrl((current) => current || latestShipment.tracking_url || '');
    }
  }, [latestShipment?.tracking_code, latestShipment?.tracking_url]);

  function invalidateOrder() {
    queryClient.invalidateQueries({ queryKey: queryKeys.order(shopId, orderId!) });
    queryClient.invalidateQueries({ queryKey: queryKeys.orders(shopId) });
    queryClient.invalidateQueries({ queryKey: queryKeys.orderCorrectness(orderId!) });
    queryClient.invalidateQueries({ queryKey: queryKeys.orderTimeline(orderId!) });
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

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Order detail</p>
        <div className="section-header section-header--stacked">
          <h1>Order {order.id.slice(0, 8)}</h1>
          <div className="order-draft-panel__meta">
            <PilotModeBadge snapshot={correctness?.pilot_mode_snapshot} />
            {correctness && <ReservationStatusChip reservations={correctness.reservations} />}
          </div>
        </div>
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
        <div className="section-header section-header--stacked">
          <div>
            <h2>Fulfillment</h2>
            <p className="dashboard-card__subtitle">
              Payment and shipping records linked to this order.
            </p>
          </div>
        </div>

        <div className="order-fulfillment-grid">
          <PaymentPanel payment={latestPayment} />
          <ShippingPanel shipment={latestShipment} />
        </div>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Operator actions</h2>
            <p className="dashboard-card__subtitle">
              Manual steps for confirming, paying, shipping, or cancelling this order.
            </p>
          </div>
        </div>

        <OperatorActionsPanel
          order={order}
          trackingCode={trackingCode}
          trackingUrl={trackingUrl}
          cancelReason={cancelReason}
          isPending={actionMutation.isPending}
          onTrackingCodeChange={setTrackingCode}
          onTrackingUrlChange={setTrackingUrl}
          onCancelReasonChange={setCancelReason}
          onConfirm={() => setPendingAction('confirm')}
          onMarkPaid={() => setPendingAction('markPaid')}
          onShipSubmit={(event) => {
            event.preventDefault();
            if (trackingCode.trim()) {
              setPendingAction('ship');
            }
          }}
          onCancelSubmit={(event) => {
            event.preventDefault();
            setPendingAction('cancel');
          }}
        />
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Audit timeline</h2>
        {orderId ? <OrderTimelineTab orderId={orderId} /> : null}
        <h3 className="context-section__title">Legacy timeline</h3>
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
