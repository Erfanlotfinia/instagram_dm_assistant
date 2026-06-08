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
    hasOrder && (orderStatus === 'waiting_for_confirmation' || orderStatus === 'waiting_for_payment');
  const canMarkPaid = hasOrder && paymentStatus !== 'paid';
  const canShip = hasOrder && orderStatus === 'paid';
  const canCancel = hasOrder && orderStatus !== 'cancelled' && orderStatus !== 'completed';

  return (
    <div className="button-row button-row--wrap" aria-label="Quick actions">
      <button className="button button--primary" type="button" onClick={onTakeOver} disabled={isLoading}>
        Take over
      </button>
      <button className="button button--ghost-dark" type="button" onClick={onRelease} disabled={isLoading}>
        Release to agent
      </button>
      <button className="button button--ghost-dark" type="button" onClick={onResolve} disabled={isLoading}>
        Mark resolved
      </button>
      <button className="button button--ghost-dark" type="button" onClick={onCreateOrder} disabled={isLoading}>
        Create order
      </button>
      {canSendPayment ? (
        <button className="button button--ghost-dark" type="button" onClick={onSendPaymentLink} disabled={isLoading}>
          Send payment link
        </button>
      ) : null}
      {canMarkPaid ? (
        <button className="button button--ghost-dark" type="button" onClick={onMarkPaid} disabled={isLoading}>
          Mark paid
        </button>
      ) : null}
      {canShip ? (
        <button className="button button--ghost-dark" type="button" onClick={onSendTracking} disabled={isLoading}>
          Send tracking
        </button>
      ) : null}
      {canCancel ? (
        <button className="button button--danger" type="button" onClick={onCancelOrder} disabled={isLoading}>
          Cancel order
        </button>
      ) : null}
    </div>
  );
}
