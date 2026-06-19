import { Badge, type BadgeTone } from '../ui';
import type { ReservationSummary } from '../../types/order';

interface ReservationStatusChipProps {
  reservations: ReservationSummary[];
}

function toneForStatus(status: ReservationSummary['status']): BadgeTone {
  switch (status) {
    case 'active':
      return 'warning';
    case 'confirmed':
      return 'success';
    case 'released':
      return 'neutral';
    case 'expired':
      return 'danger';
    default:
      return 'neutral';
  }
}

export function ReservationStatusChip({ reservations }: ReservationStatusChipProps) {
  const active = reservations.find((r) => r.status === 'active' || r.status === 'confirmed');
  if (!active) {
    return <Badge tone="neutral">No reservation</Badge>;
  }

  return (
    <Badge tone={toneForStatus(active.status)} title={`Expires ${active.expires_at}`}>
      Reserved: {active.quantity} ({active.status})
    </Badge>
  );
}
