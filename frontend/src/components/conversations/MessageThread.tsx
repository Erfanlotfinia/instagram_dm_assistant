import type { Message } from '../../types/conversation';

interface MessageThreadProps {
  messages: Message[];
  isAdmin?: boolean;
}

function formatMessageTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  if (isToday) {
    return date.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  }

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function senderLabel(message: Message): string {
  if (message.direction === 'inbound') {
    return 'Customer';
  }
  if (message.message_type === 'system') {
    return 'System';
  }
  return 'Shop';
}

export function MessageThread({ messages, isAdmin = false }: MessageThreadProps) {
  if (messages.length === 0) {
    return (
      <div className="conversation-chat__empty">
        <p className="empty-state">No messages in this conversation yet.</p>
      </div>
    );
  }

  return (
    <div className="message-thread message-thread--chat">
      {messages.map((message) => (
        <article
          key={message.id}
          className={`message-bubble message-bubble--${message.direction}${
            message.message_type === 'system' ? ' message-bubble--system' : ''
          }`}
        >
          <header className="message-bubble__header">
            <span className="message-bubble__sender">{senderLabel(message)}</span>
            <time className="message-bubble__time" dateTime={message.created_at}>
              {formatMessageTime(message.created_at)}
            </time>
          </header>
          <p className="message-bubble__text" dir="auto">
            {message.text ?? '(no text)'}
          </p>
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
