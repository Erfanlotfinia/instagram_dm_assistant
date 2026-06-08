import type { Message } from '../../types/conversation';

interface MessageThreadProps {
  messages: Message[];
  isAdmin?: boolean;
}

export function MessageThread({ messages, isAdmin = false }: MessageThreadProps) {
  if (messages.length === 0) {
    return <p className="empty-state">No messages in this conversation.</p>;
  }

  return (
    <div className="message-thread">
      {messages.map((message) => (
        <article
          key={message.id}
          className={`message-bubble message-bubble--${message.direction}`}
        >
          <p className="message-bubble__meta">
            {message.direction} · {message.message_type} ·{' '}
            {new Date(message.created_at).toLocaleString()}
          </p>
          <p className="message-bubble__text">{message.text ?? '(no text)'}</p>
          {isAdmin && message.raw_payload ? (
            <details className="message-bubble__debug">
              <summary>Raw payload</summary>
              <pre>{JSON.stringify(message.raw_payload, null, 2)}</pre>
            </details>
          ) : null}
        </article>
      ))}
    </div>
  );
}
