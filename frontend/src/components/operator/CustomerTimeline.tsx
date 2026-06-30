import { Link } from 'react-router-dom';

import { Badge, type BadgeTone } from '../ui';
import { EmptyState, LoadingState } from '../data';
import type { CustomerTimelineItem, CustomerTimelineItemType } from '../../types/sprint5Operator';
import { cn } from '../../lib/cn';

interface CustomerTimelineProps {
  items: CustomerTimelineItem[];
  isLoading?: boolean;
  error?: string | null;
  emptyTitle?: string;
  emptyDescription?: string;
}

const TYPE_TONE: Record<CustomerTimelineItemType, BadgeTone> = {
  message: 'neutral',
  order: 'accent',
  payment: 'success',
  handoff: 'warning',
  ai_decision: 'info',
  note: 'neutral',
  system: 'neutral',
};

const TYPE_LABEL: Record<CustomerTimelineItemType, string> = {
  message: 'Message',
  order: 'Order',
  payment: 'Payment',
  handoff: 'Handoff',
  ai_decision: 'AI',
  note: 'Note',
  system: 'System',
};

function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return '';
  const ms = new Date(iso).getTime();
  if (Number.isNaN(ms)) return '';
  const diff = Date.now() - ms;
  const minutes = Math.round(diff / 60_000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function CustomerTimeline({
  items,
  isLoading = false,
  error = null,
  emptyTitle = 'No timeline yet',
  emptyDescription = 'Messages, orders, payments, and AI decisions will appear here.',
}: CustomerTimelineProps) {
  if (isLoading) {
    return <LoadingState label="Loading timeline…" />;
  }
  if (error) {
    return (
      <div className="rounded-lg border border-border bg-surface p-3 text-sm text-danger">
        {error}
      </div>
    );
  }
  if (items.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <ol className="flex flex-col gap-3" aria-label="Customer timeline">
      {items.map((item) => {
        const tone = TYPE_TONE[item.type];
        const label = TYPE_LABEL[item.type];
        const relative = formatRelativeTime(item.created_at);
        return (
          <li key={item.id} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span
                className={cn(
                  'mt-1 h-2 w-2 rounded-full',
                  tone === 'danger'
                    ? 'bg-danger'
                    : tone === 'success'
                      ? 'bg-success'
                      : tone === 'warning'
                        ? 'bg-warning'
                        : tone === 'accent'
                          ? 'bg-accent'
                          : tone === 'info'
                            ? 'bg-info'
                            : 'bg-muted',
                )}
                aria-hidden="true"
              />
              {items[items.length - 1].id !== item.id ? (
                <span className="mt-1 w-px flex-1 bg-border" aria-hidden="true" />
              ) : null}
            </div>
            <div className="min-w-0 flex-1 pb-2">
              <div className="flex items-center justify-between gap-2">
                <Badge tone={tone}>{label}</Badge>
                {relative ? (
                  <time
                    className="text-xs text-subtle"
                    dateTime={item.created_at ?? undefined}
                    title={item.created_at ?? undefined}
                  >
                    {relative}
                  </time>
                ) : null}
              </div>
              <p className="mt-1 text-sm text-fg">{item.title}</p>
              {item.description ? (
                <p className="mt-0.5 line-clamp-2 text-xs text-muted">{item.description}</p>
              ) : null}
              {item.action_to ? (
                <Link
                  to={item.action_to}
                  className="mt-1 inline-block text-xs text-accent hover:underline"
                >
                  Open →
                </Link>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
