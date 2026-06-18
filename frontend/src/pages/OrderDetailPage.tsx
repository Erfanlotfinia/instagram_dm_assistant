import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { OrderTimelineTab } from '../components/orders/OrderTimelineTab';
import { PilotModeBadge } from '../components/orders/PilotModeBadge';
import { ReservationStatusChip } from '../components/orders/ReservationStatusChip';
import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input } from '../components/ui';
import type { BadgeTone } from '../components/ui';
import { DataTable, EmptyState, LoadingState } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { cn } from '../lib/cn';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { OrderItem, Payment, Shipment } from '../types/order';
import type { PaymentRecordStatus, ShipmentStatus } from '../types/orderEnums';

type PendingAction = 'markPaid' | 'ship' | 'cancel' | 'confirm' | null;

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

function paymentStatusTone(status: PaymentRecordStatus): BadgeTone {
  if (status === 'paid') return 'success';
  if (status === 'pending' || status === 'created') return 'warning';
  if (status === 'failed' || status === 'cancelled') return 'danger';
  return 'neutral';
}

function shipmentStatusTone(status: ShipmentStatus): BadgeTone {
  if (status === 'delivered' || status === 'shipped') return 'success';
  if (status === 'preparing' || status === 'pending') return 'warning';
  if (status === 'failed') return 'danger';
  return 'neutral';
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
    <div className="flex flex-col gap-0.5">
      <span className="text-xs font-medium text-muted">{label}</span>
      <span className={cn('text-sm text-fg', mono && 'font-mono')}>{value}</span>
    </div>
  );
}

function PaymentPanel({ payment }: { payment: Payment | undefined }) {
  if (!payment) {
    return (
      <Card as="article">
        <CardHeader title="Payment" actions={<Badge tone="neutral">No record</Badge>} />
        <CardBody>
          <p className="text-sm text-muted">No payment has been initiated for this order yet.</p>
        </CardBody>
      </Card>
    );
  }

  const recordedAt = formatDateTime(payment.updated_at ?? payment.created_at);

  return (
    <Card as="article">
      <CardHeader
        title="Payment"
        description={providerLabel(payment.provider)}
        actions={<Badge tone={paymentStatusTone(payment.status)}>{PAYMENT_STATUS_LABELS[payment.status]}</Badge>}
      />
      <CardBody className="flex flex-col gap-3">
        {payment.provider_reference ? (
          <FulfillmentField label="Reference" value={payment.provider_reference} mono />
        ) : null}
        {recordedAt ? <FulfillmentField label="Last updated" value={recordedAt} /> : null}

        {payment.payment_url ? (
          <div className="flex flex-wrap items-center gap-2">
            <a
              className="inline-flex h-8 items-center rounded-lg border border-border bg-surface px-3 text-xs font-medium text-fg hover:bg-surface-sunken"
              href={payment.payment_url}
              target="_blank"
              rel="noreferrer"
            >
              Open payment page
            </a>
            <span className="truncate text-xs text-subtle" title={payment.payment_url}>
              Demo checkout link
            </span>
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}

function OperatorActionRow({
  title,
  description,
  buttonLabel,
  buttonVariant = 'secondary',
  disabled,
  unavailableReason,
  completed = false,
  completedLabel = 'Done',
  onClick,
}: {
  title: string;
  description: string;
  buttonLabel: string;
  buttonVariant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  disabled: boolean;
  unavailableReason?: string;
  completed?: boolean;
  completedLabel?: string;
  onClick: () => void;
}) {
  if (completed) {
    return (
      <li className="flex items-start justify-between gap-3 rounded-md border border-success/30 bg-success-soft/20 px-3 py-3">
        <div>
          <strong className="text-sm text-fg">{title}</strong>
          <p className="mt-0.5 text-xs text-muted">{description}</p>
        </div>
        <Badge tone="success">{completedLabel}</Badge>
      </li>
    );
  }

  return (
    <li
      className={cn(
        'flex items-start justify-between gap-3 rounded-md border border-border px-3 py-3',
        disabled && 'opacity-60',
      )}
    >
      <div>
        <strong className="text-sm text-fg">{title}</strong>
        <p className="mt-0.5 text-xs text-muted">{disabled && unavailableReason ? unavailableReason : description}</p>
      </div>
      <Button variant={buttonVariant} size="sm" type="button" onClick={onClick} disabled={disabled}>
        {buttonLabel}
      </Button>
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
    <div className="grid gap-4 lg:grid-cols-2">
      <Card as="article">
        <CardHeader
          title="Payment & confirmation"
          description="Step 1"
          actions={
            <div className="flex flex-wrap gap-1.5">
              <Badge tone="neutral">{humanize(order.status)}</Badge>
              <Badge
                tone={
                  order.payment_status === 'paid'
                    ? 'success'
                    : order.payment_status === 'pending'
                      ? 'warning'
                      : 'neutral'
                }
              >
                Payment: {humanize(order.payment_status)}
              </Badge>
            </div>
          }
        />
        <CardBody>
          <ul className="flex flex-col gap-2">
            <OperatorActionRow
              title="Confirm order"
              description="Reserve inventory and send the customer to checkout."
              unavailableReason="Available when the order is draft or awaiting confirmation."
              buttonLabel="Confirm"
              buttonVariant="primary"
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
        </CardBody>
      </Card>

      <Card as="article">
        <CardHeader title="Ship order" description="Step 2" />
        <CardBody className="flex flex-col gap-3">
          <p className="text-xs text-muted">Add tracking details and notify the customer when the package leaves.</p>
          <form className="flex flex-col gap-3" onSubmit={onShipSubmit}>
            <Field label="Tracking code">
              <Input
                value={trackingCode}
                onChange={(event) => onTrackingCodeChange(event.target.value)}
                placeholder="e.g. DEMO-123456"
                disabled={isPending || !canShip}
                required
              />
            </Field>
            <Field label="Tracking URL">
              <Input
                value={trackingUrl}
                onChange={(event) => onTrackingUrlChange(event.target.value)}
                placeholder="https://tracking.example.com/..."
                disabled={isPending || !canShip}
              />
            </Field>
            <Button type="submit" disabled={isPending || !canShip || !trackingCode.trim()}>
              {isPending ? 'Saving…' : 'Ship order'}
            </Button>
          </form>
          {!canShip ? (
            <p className="text-xs text-subtle">Shipping is available after the order is paid.</p>
          ) : null}
        </CardBody>
      </Card>

      <Card as="article" className="lg:col-span-2">
        <CardHeader title="Cancel order" description="Danger zone" />
        <CardBody className="flex flex-col gap-3">
          <p className="text-xs text-danger">
            Releases inventory reservations and closes the order permanently.
          </p>
          <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={onCancelSubmit}>
            <Field label="Cancel reason" className="flex-1">
              <Input
                value={cancelReason}
                onChange={(event) => onCancelReasonChange(event.target.value)}
                placeholder="Optional note for the audit trail"
                disabled={isPending || !canCancel}
              />
            </Field>
            <Button variant="danger" type="submit" disabled={isPending || !canCancel}>
              Cancel order
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}

function ShippingPanel({ shipment }: { shipment: Shipment | undefined }) {
  if (!shipment) {
    return (
      <Card as="article">
        <CardHeader title="Shipping" actions={<Badge tone="neutral">Not started</Badge>} />
        <CardBody>
          <p className="text-sm text-muted">
            Shipment has not been created yet. Use operator actions below to ship this order.
          </p>
        </CardBody>
      </Card>
    );
  }

  const shippedAt = formatDateTime(shipment.shipped_at ?? shipment.created_at);

  return (
    <Card as="article">
      <CardHeader
        title="Shipping"
        description={providerLabel(shipment.provider)}
        actions={<Badge tone={shipmentStatusTone(shipment.status)}>{SHIPMENT_STATUS_LABELS[shipment.status]}</Badge>}
      />
      <CardBody className="flex flex-col gap-3">
        <FulfillmentField label="Tracking code" value={shipment.tracking_code ?? '—'} mono />
        {shippedAt ? <FulfillmentField label="Shipped at" value={shippedAt} /> : null}

        {shipment.tracking_url ? (
          <a
            className="inline-flex h-8 w-fit items-center rounded-lg border border-border bg-surface px-3 text-xs font-medium text-fg hover:bg-surface-sunken"
            href={shipment.tracking_url}
            target="_blank"
            rel="noreferrer"
          >
            Track shipment
          </a>
        ) : null}
      </CardBody>
    </Card>
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
      <HubPage eyebrow="Orders" title="Order detail">
        <Card>
          <CardBody className="flex flex-col gap-3">
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
            <Link className="font-medium text-accent hover:underline" to="/orders">
              Back to orders
            </Link>
          </CardBody>
        </Card>
      </HubPage>
    );
  }

  if (orderQuery.isLoading) {
    return (
      <HubPage eyebrow="Orders" title="Order detail">
        <Card>
          <CardBody>
            <LoadingState label="Loading order…" />
          </CardBody>
        </Card>
      </HubPage>
    );
  }

  if (orderQuery.error || !order) {
    return (
      <HubPage eyebrow="Orders" title="Order detail">
        <Card>
          <CardBody className="flex flex-col gap-3">
            <p className="text-sm text-danger">
              {orderQuery.error instanceof Error ? orderQuery.error.message : 'Order not found'}
            </p>
            <Link className="font-medium text-accent hover:underline" to="/orders">
              Back to orders
            </Link>
          </CardBody>
        </Card>
      </HubPage>
    );
  }

  const latestPayment = order.payments?.[0];

  const itemColumns: Column<OrderItem>[] = [
    { key: 'product', header: 'Product', render: (item) => item.product_title_snapshot },
    {
      key: 'variant',
      header: 'Variant',
      render: (item) =>
        [item.variant_color_snapshot, item.variant_size_snapshot].filter(Boolean).join(' / ') || '—',
    },
    { key: 'sku', header: 'SKU', render: (item) => item.sku_snapshot },
    { key: 'qty', header: 'Qty', render: (item) => item.quantity },
    { key: 'unit', header: 'Unit', render: (item) => item.unit_price },
    { key: 'total', header: 'Total', render: (item) => item.total_price },
  ];

  return (
    <HubPage
      eyebrow="Order detail"
      title={`Order ${order.id.slice(0, 8)}`}
      description={
        <>
          <Link className="font-medium text-accent hover:underline" to="/orders">
            Back to orders
          </Link>
          {' · '}
          <Link className="font-medium text-accent hover:underline" to={`/conversations/${order.conversation_id}?shopId=${shopId}`}>
            View conversation
          </Link>
        </>
      }
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <PilotModeBadge snapshot={correctness?.pilot_mode_snapshot} />
          {correctness ? <ReservationStatusChip reservations={correctness.reservations} /> : null}
        </div>
      }
    >
      <Card>
        <CardHeader title="Order summary" />
        <CardBody>
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
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Items" />
        <DataTable
          columns={itemColumns}
          rows={order.items}
          rowKey={(item) => item.id}
          emptyTitle="No line items"
        />
      </Card>

      <Card>
        <CardHeader title="Fulfillment" description="Payment and shipping records linked to this order." />
        <CardBody>
          <div className="grid gap-4 lg:grid-cols-2">
            <PaymentPanel payment={latestPayment} />
            <ShippingPanel shipment={latestShipment} />
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Operator actions"
          description="Manual steps for confirming, paying, shipping, or cancelling this order."
        />
        <CardBody>
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
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Audit timeline" />
        <CardBody className="flex flex-col gap-4">
          {orderId ? <OrderTimelineTab orderId={orderId} /> : null}
          <div>
            <h3 className="mb-3 text-sm font-semibold text-fg">Legacy timeline</h3>
            <ol className="space-y-2 text-sm">
              {order.timeline.map((event) => (
                <li key={`${event.status}-${event.occurred_at}`} className="rounded-md border border-border px-3 py-2">
                  <strong className="text-fg">{event.label}</strong>
                  <span className="mt-0.5 block text-xs text-muted">
                    {new Date(event.occurred_at).toLocaleString()} · {event.source}
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </CardBody>
      </Card>

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
    </HubPage>
  );
}
