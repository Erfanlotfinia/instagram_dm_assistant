import { Badge } from '../ui';
import { EmptyState } from '../data';
import type { OrderCorrectnessRead } from '../../types/order';
import { PilotModeBadge } from './PilotModeBadge';
import { ReservationStatusChip } from './ReservationStatusChip';

interface OrderDraftPanelProps {
  order: OrderCorrectnessRead;
}

export function OrderDraftPanel({ order }: OrderDraftPanelProps) {
  return (
    <section className="flex flex-col gap-3 rounded-lg border border-border bg-surface-sunken p-3" aria-label="Order draft">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Order draft</h3>
        <PilotModeBadge snapshot={order.pilot_mode_snapshot} />
      </div>

      <div className="flex flex-wrap gap-2">
        <ReservationStatusChip reservations={order.reservations} />
        {order.confidence_score ? <Badge tone="accent">Confidence: {order.confidence_score}</Badge> : null}
        {order.expires_at ? (
          <Badge tone="warning">Expires: {new Date(order.expires_at).toLocaleString()}</Badge>
        ) : null}
      </div>

      {order.draft_items.length > 0 ? (
        <ul className="space-y-1 text-sm text-fg">
          {order.draft_items.map((item) => (
            <li key={item.id}>
              {item.product_title_snapshot} — {item.variant_label_snapshot} × {item.quantity} @ {item.unit_price}
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState title="No draft line items" />
      )}

      <dl className="grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs text-muted">Total</dt>
          <dd className="font-medium text-fg">
            {order.total_amount} {order.currency}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Customer confirmed</dt>
          <dd className="text-fg">
            {order.customer_confirmed_at ? new Date(order.customer_confirmed_at).toLocaleString() : 'No'}
          </dd>
        </div>
      </dl>
    </section>
  );
}
