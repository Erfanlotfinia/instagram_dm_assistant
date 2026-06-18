import { Fragment, useEffect, useRef } from 'react';

import { EmptyState } from '../data';
import { cn } from '../../lib/cn';
import type { Message } from '../../types/conversation';

interface MessageThreadProps {
  messages: Message[];
}

const GROUPING_WINDOW_MS = 5 * 60 * 1000;

function formatMessageTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  if (date.toDateString() === now.toDateString()) {
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
  if (date.toDateString() === now.toDateString()) return 'Today';
  if (date.toDateString() === yesterday.toDateString()) return 'Yesterday';
  const sameYear = date.getFullYear() === now.getFullYear();
  return date.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    ...(sameYear ? {} : { year: 'numeric' }),
  });
}

function senderLabel(message: Message): string {
  if (message.direction === 'inbound') return 'Customer';
  if (message.message_type === 'system') return 'System';
  return 'Shop';
}

function isSameDay(a: string, b: string): boolean {
  return new Date(a).toDateString() === new Date(b).toDateString();
}

function isGroupedWithPrevious(current: Message, previous: Message | undefined): boolean {
  if (!previous) return false;
  if (current.message_type === 'system' || previous.message_type === 'system') return false;
  if (current.direction !== previous.direction) return false;
  if (!isSameDay(current.created_at, previous.created_at)) return false;
  const delta = new Date(current.created_at).getTime() - new Date(previous.created_at).getTime();
  return delta >= 0 && delta < GROUPING_WINDOW_MS;
}

export function MessageThread({ messages }: MessageThreadProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = endRef.current;
    if (node && typeof node.scrollIntoView === 'function') {
      node.scrollIntoView({ block: 'nearest' });
    }
  }, [messages.length]);

  if (messages.length === 0) {
    return (
      <EmptyState title="No messages yet" description="No messages in this conversation yet." />
    );
  }

  return (
    <div className="flex flex-col gap-2" role="log" aria-live="polite" aria-label="Conversation messages">
      {messages.map((message, index) => {
        const previous = messages[index - 1];
        const showDayDivider = !previous || !isSameDay(previous.created_at, message.created_at);
        const grouped = !showDayDivider && isGroupedWithPrevious(message, previous);
        const inbound = message.direction === 'inbound';
        const isSystem = message.message_type === 'system';

        return (
          <Fragment key={message.id}>
            {showDayDivider ? (
              <div className="flex items-center gap-3 py-2" role="separator">
                <div className="h-px flex-1 bg-border" />
                <span className="text-xs font-medium text-subtle">{formatDayDivider(message.created_at)}</span>
                <div className="h-px flex-1 bg-border" />
              </div>
            ) : null}
            <article
              className={cn(
                'flex max-w-[85%] flex-col gap-0.5',
                inbound ? 'self-start' : 'self-end items-end',
                grouped && 'mt-0.5',
              )}
            >
              {!grouped ? (
                <header className="flex items-center gap-2 px-1 text-xs text-subtle">
                  <span>{senderLabel(message)}</span>
                  <time dateTime={message.created_at}>{formatMessageTime(message.created_at)}</time>
                </header>
              ) : (
                <time className="px-1 text-[10px] text-subtle" dateTime={message.created_at}>
                  {formatMessageTime(message.created_at)}
                </time>
              )}
              <div
                className={cn(
                  'rounded-2xl px-3 py-2 text-sm leading-relaxed',
                  isSystem && 'w-full max-w-none self-center rounded-lg bg-surface-sunken text-center text-xs text-muted',
                  !isSystem && inbound && 'rounded-bl-md bg-surface-sunken text-fg',
                  !isSystem && !inbound && 'rounded-br-md bg-accent text-accent-fg',
                )}
                dir="auto"
              >
                {message.text ?? '(no text)'}
                {message.raw_payload?.callback_query ? (
                  <p className="mt-1 text-xs opacity-70">Telegram callback query event</p>
                ) : null}
                {message.raw_payload?.status ? (
                  <p className="mt-1 text-xs opacity-70">
                    Delivery: {String((message.raw_payload.status as Record<string, unknown>).status ?? 'unknown')}
                  </p>
                ) : null}
              </div>
            </article>
          </Fragment>
        );
      })}
      <div ref={endRef} aria-hidden="true" />
    </div>
  );
}
