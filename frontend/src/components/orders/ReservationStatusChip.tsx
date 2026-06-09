import type { ReservationSummary } from '../../types/order';

interface ReservationStatusChipProps {
  reservations: ReservationSummary[];
}

function toneForStatus(status: ReservationSummary['status']): string {
  switch (status) {
    case 'active':
      return 'status-pill--warning';
    case 'confirmed':
      return 'status-pill--success';
    case 'released':
      return 'status-pill--neutral';
    case 'expired':
      return 'status-pill--danger';
    default:
      return 'status-pill--neutral';
  }
}

export function ReservationStatusChip({ reservations }: ReservationStatusChipProps) {
  const active = reservations.find((r) => r.status === 'active' || r.status === 'confirmed');
  if (!active) {
    return <span className="status-pill status-pill--neutral">No reservation</span>;
  }

  return (
    <span className={`status-pill ${toneForStatus(active.status)}`} title={`Expires ${active.expires_at}`}>
      Reserved: {active.quantity} ({active.status})
    </span>
  );
}
