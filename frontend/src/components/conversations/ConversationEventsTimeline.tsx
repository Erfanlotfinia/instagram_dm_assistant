import type { ConversationEvent, ConversationEventType } from '../../types/conversation';

interface ConversationEventsTimelineProps {
  events: ConversationEvent[];
}

type EventTone = 'message' | 'agent' | 'order' | 'payment' | 'handoff' | 'operator' | 'neutral';

const EVENT_META: Record<ConversationEventType, { label: string; tone: EventTone }> = {
  inbound_message_received: { label: 'Message received', tone: 'message' },
  outbound_message_sent: { label: 'Message sent', tone: 'message' },
  suggested_reply_created: { label: 'Suggested reply', tone: 'agent' },
  suggested_reply_approved: { label: 'Reply approved', tone: 'agent' },
  product_resolved: { label: 'Product matched', tone: 'agent' },
  variant_resolved: { label: 'Variant matched', tone: 'agent' },
  inventory_checked: { label: 'Inventory checked', tone: 'agent' },
  draft_order_created: { label: 'Draft order', tone: 'order' },
  customer_info_completed: { label: 'Customer info', tone: 'order' },
  confirmation_requested: { label: 'Confirmation', tone: 'order' },
  payment_link_sent: { label: 'Payment link', tone: 'payment' },
  payment_received: { label: 'Payment received', tone: 'payment' },
  order_shipped: { label: 'Order shipped', tone: 'order' },
  handoff_required: { label: 'Handoff', tone: 'handoff' },
  operator_took_over: { label: 'Operator takeover', tone: 'operator' },
  operator_released_to_agent: { label: 'Released to agent', tone: 'operator' },
  order_cancelled: { label: 'Order cancelled', tone: 'order' },
  conversation_assigned: { label: 'Assigned', tone: 'operator' },
  customer_profile_updated: { label: 'Profile updated', tone: 'neutral' },
};

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) {
    return iso;
  }
  const diffMs = Date.now() - then;
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatDayLabel(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);

  if (date.toDateString() === now.toDateString()) {
    return 'Today';
  }
  if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday';
  }
  return date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}

function isSameDay(a: string, b: string): boolean {
  return new Date(a).toDateString() === new Date(b).toDateString();
}

export function ConversationEventsTimeline({ events }: ConversationEventsTimelineProps) {
  if (events.length === 0) {
    return (
      <div className="activity-timeline activity-timeline--empty">
        <p className="empty-state">No conversation events yet.</p>
        <p className="activity-timeline__hint">Events appear when messages arrive, orders progress, or operators take action.</p>
      </div>
    );
  }

  return (
    <ol className="activity-timeline" aria-label="Conversation activity">
      {events.map((event, index) => {
        const meta = EVENT_META[event.event_type] ?? { label: event.title, tone: 'neutral' as EventTone };
        const previous = events[index - 1];
        const showDay = !previous || !isSameDay(previous.created_at, event.created_at);

        return (
          <li key={event.id} className="activity-timeline__item">
            {showDay ? (
              <div className="activity-timeline__day" aria-hidden="true">
                {formatDayLabel(event.created_at)}
              </div>
            ) : null}
            <div className={`activity-timeline__card activity-timeline__card--${meta.tone}`}>
              <div className="activity-timeline__marker" aria-hidden="true" />
              <div className="activity-timeline__content">
                <div className="activity-timeline__head">
                  <span className={`activity-timeline__badge activity-timeline__badge--${meta.tone}`}>
                    {meta.label}
                  </span>
                  <time
                    className="activity-timeline__time"
                    dateTime={event.created_at}
                    title={new Date(event.created_at).toLocaleString()}
                  >
                    {formatRelativeTime(event.created_at)}
                  </time>
                </div>
                <p className="activity-timeline__title">{event.title}</p>
                {event.description ? (
                  <p className="activity-timeline__desc">{event.description}</p>
                ) : null}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
