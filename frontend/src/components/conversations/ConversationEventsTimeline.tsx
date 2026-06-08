import type { ConversationEvent } from '../../types/conversation';

interface ConversationEventsTimelineProps {
  events: ConversationEvent[];
}

export function ConversationEventsTimeline({ events }: ConversationEventsTimelineProps) {
  if (events.length === 0) {
    return <p className="empty-state">No conversation events yet.</p>;
  }

  return (
    <ul className="event-timeline">
      {events.map((event) => (
        <li key={event.id} className="event-timeline__item">
          <p className="event-timeline__title">{event.title}</p>
          <p className="event-timeline__meta">
            {event.event_type} · {new Date(event.created_at).toLocaleString()}
          </p>
          {event.description ? <p className="event-timeline__desc">{event.description}</p> : null}
        </li>
      ))}
    </ul>
  );
}
