import { Button } from '../ui';

interface OperatorQuickActionsProps {
  hasOrder: boolean;
  orderStatus?: string;
  paymentStatus?: string;
  onTakeOver: () => void;
  onRelease: () => void;
  onResolve: () => void;
  onCreateOrder: () => void;
  onSendPaymentLink: () => void;
  onMarkPaid: () => void;
  onSendTracking: () => void;
  onCancelOrder: () => void;
  isLoading?: boolean;
}

export function OperatorQuickActions({
  hasOrder,
  orderStatus,
  paymentStatus,
  onTakeOver,
  onRelease,
  onResolve,
  onCreateOrder,
  onSendPaymentLink,
  onMarkPaid,
  onSendTracking,
  onCancelOrder,
  isLoading,
}: OperatorQuickActionsProps) {
  const canSendPayment =
    hasOrder &&
    (orderStatus === 'ready_for_confirmation' ||
      orderStatus === 'reserved' ||
      orderStatus === 'payment_pending' ||
      orderStatus === 'waiting_for_payment');
  const canMarkPaid = hasOrder && paymentStatus !== 'paid';
  const canShip = hasOrder && orderStatus === 'paid';
  const canCancel = hasOrder && orderStatus !== 'cancelled' && orderStatus !== 'completed';

  return (
    <div className="flex flex-col gap-4" aria-label="Quick actions">
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Handoff</p>
        <div className="flex flex-wrap gap-2">
          <Button type="button" size="sm" onClick={onTakeOver} disabled={isLoading}>
            Take over
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={onRelease} disabled={isLoading}>
            Release to agent
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={onResolve} disabled={isLoading}>
            Mark resolved
          </Button>
        </div>
      </div>

      <div className="h-px bg-border" aria-hidden="true" />

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Order</p>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="secondary" size="sm" onClick={onCreateOrder} disabled={isLoading}>
            Create order
          </Button>
          {canSendPayment ? (
            <Button type="button" variant="secondary" size="sm" onClick={onSendPaymentLink} disabled={isLoading}>
              Send payment link
            </Button>
          ) : null}
          {canMarkPaid ? (
            <Button type="button" variant="secondary" size="sm" onClick={onMarkPaid} disabled={isLoading}>
              Mark paid
            </Button>
          ) : null}
          {canShip ? (
            <Button type="button" variant="secondary" size="sm" onClick={onSendTracking} disabled={isLoading}>
              Send tracking
            </Button>
          ) : null}
          {canCancel ? (
            <Button type="button" variant="danger" size="sm" onClick={onCancelOrder} disabled={isLoading}>
              Cancel order
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
