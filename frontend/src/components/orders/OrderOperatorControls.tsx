import { useState } from 'react';

import { ConfirmDialog } from '../ConfirmDialog';

interface OrderOperatorControlsProps {
  canApprove: boolean;
  canReject: boolean;
  canCancel: boolean;
  onApprove: () => void;
  onReject: (reason: string) => void;
  onCancel: (reason: string) => void;
  isApproving?: boolean;
  isRejecting?: boolean;
  isCancelling?: boolean;
}

export function OrderOperatorControls({
  canApprove,
  canReject,
  canCancel,
  onApprove,
  onReject,
  onCancel,
  isApproving,
  isRejecting,
  isCancelling,
}: OrderOperatorControlsProps) {
  const [rejectOpen, setRejectOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [cancelReason, setCancelReason] = useState('');

  return (
    <div className="order-operator-controls">
      {canApprove && (
        <button className="button button--primary" type="button" onClick={onApprove} disabled={isApproving}>
          Approve order
        </button>
      )}
      {canReject && (
        <button
          className="button button--secondary"
          type="button"
          onClick={() => setRejectOpen(true)}
          disabled={isRejecting}
        >
          Reject
        </button>
      )}
      {canCancel && (
        <button className="button button--ghost" type="button" onClick={() => setCancelOpen(true)} disabled={isCancelling}>
          Cancel order
        </button>
      )}

      {rejectOpen && (
        <div className="form-field">
          <label>
            <span>Reject reason</span>
            <input type="text" value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} />
          </label>
        </div>
      )}

      <ConfirmDialog
        open={rejectOpen}
        title="Reject order"
        message="Rejecting will cancel the order and release any reservation."
        confirmLabel="Reject"
        onConfirm={() => {
          onReject(rejectReason);
          setRejectOpen(false);
          setRejectReason('');
        }}
        onCancel={() => setRejectOpen(false)}
        isLoading={isRejecting}
      />

      {cancelOpen && (
        <div className="form-field">
          <label>
            <span>Cancel reason</span>
            <input type="text" value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} />
          </label>
        </div>
      )}

      <ConfirmDialog
        open={cancelOpen}
        title="Cancel order"
        message="This releases inventory reservations."
        confirmLabel="Cancel order"
        onConfirm={() => {
          onCancel(cancelReason);
          setCancelOpen(false);
          setCancelReason('');
        }}
        onCancel={() => setCancelOpen(false)}
        isLoading={isCancelling}
      />
    </div>
  );
}
