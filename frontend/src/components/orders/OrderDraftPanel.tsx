import type { OrderCorrectnessRead } from '../../types/order';
import { PilotModeBadge } from './PilotModeBadge';
import { ReservationStatusChip } from './ReservationStatusChip';

interface OrderDraftPanelProps {
  order: OrderCorrectnessRead;
}

export function OrderDraftPanel({ order }: OrderDraftPanelProps) {
  return (
    <section className="order-draft-panel dashboard-card" aria-label="Order draft">
      <div className="order-draft-panel__header">
        <h3 className="context-section__title">Order draft</h3>
        <PilotModeBadge snapshot={order.pilot_mode_snapshot} />
      </div>

      <div className="order-draft-panel__meta">
        <span className="status-pill status-pill--neutral">{order.status.replace(/_/g, ' ')}</span>
        <ReservationStatusChip reservations={order.reservations} />
        {order.confidence_score && (
          <span className="status-pill status-pill--accent">Confidence: {order.confidence_score}</span>
        )}
        {order.expires_at && (
          <span className="status-pill status-pill--warning">Expires: {new Date(order.expires_at).toLocaleString()}</span>
        )}
      </div>

      {order.draft_items.length > 0 ? (
        <ul className="order-draft-panel__items">
          {order.draft_items.map((item) => (
            <li key={item.id}>
              {item.product_title_snapshot} — {item.variant_label_snapshot} × {item.quantity} @ {item.unit_price}
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty-state">No draft line items.</p>
      )}

      <dl className="context-facts">
        <div className="context-facts__item">
          <dt>Total</dt>
          <dd>{order.total_amount} {order.currency}</dd>
        </div>
        <div className="context-facts__item">
          <dt>Customer confirmed</dt>
          <dd>{order.customer_confirmed_at ? new Date(order.customer_confirmed_at).toLocaleString() : 'No'}</dd>
        </div>
      </dl>
    </section>
  );
}
