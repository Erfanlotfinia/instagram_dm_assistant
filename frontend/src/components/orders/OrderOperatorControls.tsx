import { useState } from 'react';

import { Button, Dialog, Field, Input } from '../ui';

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
    <div className="flex flex-wrap gap-2">
      {canApprove ? (
        <Button type="button" size="sm" onClick={onApprove} disabled={isApproving}>
          Approve order
        </Button>
      ) : null}
      {canReject ? (
        <Button type="button" variant="secondary" size="sm" onClick={() => setRejectOpen(true)} disabled={isRejecting}>
          Reject
        </Button>
      ) : null}
      {canCancel ? (
        <Button type="button" variant="ghost" size="sm" onClick={() => setCancelOpen(true)} disabled={isCancelling}>
          Cancel order
        </Button>
      ) : null}

      <Dialog
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        title="Reject order"
        footer={
          <>
            <Button variant="secondary" size="sm" type="button" onClick={() => setRejectOpen(false)} disabled={isRejecting}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              type="button"
              disabled={isRejecting}
              onClick={() => {
                onReject(rejectReason);
                setRejectOpen(false);
                setRejectReason('');
              }}
            >
              {isRejecting ? 'Working…' : 'Reject'}
            </Button>
          </>
        }
      >
        <p className="mb-3 text-sm text-muted">Rejecting will cancel the order and release any reservation.</p>
        <Field label="Reject reason" htmlFor="reject-reason">
          <Input id="reject-reason" value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} />
        </Field>
      </Dialog>

      <Dialog
        open={cancelOpen}
        onClose={() => setCancelOpen(false)}
        title="Cancel order"
        footer={
          <>
            <Button variant="secondary" size="sm" type="button" onClick={() => setCancelOpen(false)} disabled={isCancelling}>
              Back
            </Button>
            <Button
              variant="danger"
              size="sm"
              type="button"
              disabled={isCancelling}
              onClick={() => {
                onCancel(cancelReason);
                setCancelOpen(false);
                setCancelReason('');
              }}
            >
              {isCancelling ? 'Working…' : 'Cancel order'}
            </Button>
          </>
        }
      >
        <p className="mb-3 text-sm text-muted">This releases inventory reservations.</p>
        <Field label="Cancel reason" htmlFor="cancel-reason">
          <Input id="cancel-reason" value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} />
        </Field>
      </Dialog>
    </div>
  );
}
