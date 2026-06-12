import { Fragment, useEffect, useRef } from 'react';

import type { Message } from '../../types/conversation';

interface MessageThreadProps {
  messages: Message[];
}

// Messages from the same sender within this window are visually grouped.
const GROUPING_WINDOW_MS = 5 * 60 * 1000;

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

function formatDayDivider(iso: string): string {
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

  const sameYear = date.getFullYear() === now.getFullYear();
  return date.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    ...(sameYear ? {} : { year: 'numeric' }),
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

function isSameDay(a: string, b: string): boolean {
  return new Date(a).toDateString() === new Date(b).toDateString();
}

function isGroupedWithPrevious(current: Message, previous: Message | undefined): boolean {
  if (!previous) {
    return false;
  }
  if (current.message_type === 'system' || previous.message_type === 'system') {
    return false;
  }
  if (current.direction !== previous.direction) {
    return false;
  }
  if (!isSameDay(current.created_at, previous.created_at)) {
    return false;
  }
  const delta = new Date(current.created_at).getTime() - new Date(previous.created_at).getTime();
  return delta >= 0 && delta < GROUPING_WINDOW_MS;
}

export function MessageThread({ messages }: MessageThreadProps) {
  const endRef = useRef<HTMLDivElement>(null);

  // Keep the latest message in view as the conversation grows.
  useEffect(() => {
    const node = endRef.current;
    if (node && typeof node.scrollIntoView === 'function') {
      node.scrollIntoView({ block: 'nearest' });
    }
  }, [messages.length]);

  if (messages.length === 0) {
    return (
      <div className="conversation-chat__empty">
        <p className="empty-state">No messages in this conversation yet.</p>
      </div>
    );
  }

  return (
    <div
      className="message-thread message-thread--chat"
      role="log"
      aria-live="polite"
      aria-label="Conversation messages"
    >
      {messages.map((message, index) => {
        const previous = messages[index - 1];
        const showDayDivider = !previous || !isSameDay(previous.created_at, message.created_at);
        const grouped = !showDayDivider && isGroupedWithPrevious(message, previous);

        return (
          <Fragment key={message.id}>
            {showDayDivider ? (
              <div className="message-thread__day" role="separator">
                <span>{formatDayDivider(message.created_at)}</span>
              </div>
            ) : null}
            <article
              className={`message-bubble message-bubble--${message.direction}${
                message.message_type === 'system' ? ' message-bubble--system' : ''
              }${grouped ? ' message-bubble--grouped' : ''}`}
            >
              <header className="message-bubble__header">
                {!grouped ? (
                  <span className="message-bubble__sender">{senderLabel(message)}</span>
                ) : null}
                <time className="message-bubble__time" dateTime={message.created_at}>
                  {formatMessageTime(message.created_at)}
                </time>
              </header>
              <p className="message-bubble__text" dir="auto">
                {message.text ?? '(no text)'}
              </p>
              {message.raw_payload?.callback_query ? <small>Telegram callback query event</small> : null}
              {message.raw_payload?.status ? <small>Delivery status: {String((message.raw_payload.status as Record<string, unknown>).status ?? 'unknown')}</small> : null}
            </article>
          </Fragment>
        );
      })}
      <div ref={endRef} aria-hidden="true" />
    </div>
  );
}
