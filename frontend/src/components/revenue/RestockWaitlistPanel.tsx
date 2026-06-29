import { useState } from 'react';
import { Link } from 'react-router-dom';

import { Badge, Button, Card, CardBody, CardHeader } from '../ui';
import { EmptyState, ErrorState, LoadingState } from '../data';
import type { BadgeTone } from '../ui';
import type { RestockWaitlistItem, RestockWaitlistStatus } from '../../types/sprint4Revenue';

export interface RestockWaitlistPanelProps {
  items: RestockWaitlistItem[];
  isLoading?: boolean;
  error?: string | null;
}

function statusTone(status: RestockWaitlistStatus): BadgeTone {
  if (status === 'converted') return 'success';
  if (status === 'notified') return 'info';
  if (status === 'dismissed') return 'neutral';
  return 'warning';
}

function copyToClipboard(text: string): void {
  if (typeof navigator !== 'undefined' && navigator.clipboard) {
    void navigator.clipboard.writeText(text);
  }
}

/**
 * Restock waitlist derived from unavailable demand logs where a customer or
 * conversation is known. Grouped by product. Read-only — no status mutation
 * (no API exists for it). Suggested messages are preview-only and must not
 * be sent automatically.
 */
export function RestockWaitlistPanel({ items, isLoading, error }: RestockWaitlistPanelProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const groups = new Map<string, { productLabel: string; productId?: string | null; rows: RestockWaitlistItem[] }>();
  for (const item of items) {
    const key = item.product_id ?? item.product_label;
    const existing = groups.get(key) ?? { productLabel: item.product_label, productId: item.product_id, rows: [] };
    existing.rows.push(item);
    groups.set(key, existing);
  }
  const grouped = Array.from(groups.values());

  return (
    <Card>
      <CardHeader
        title="Restock waitlist"
        description="Customers who asked for an unavailable item. Messages are preview-only — copy and send manually from the conversation."
      />
      <CardBody className="flex flex-col gap-4">
        {isLoading ? (
          <LoadingState label="Loading waitlist…" />
        ) : error ? (
          <ErrorState message={error} />
        ) : grouped.length === 0 ? (
          <EmptyState
            title="No waitlist entries yet"
            description="When customers ask for out-of-stock items, they'll appear here so you can notify them on restock."
          />
        ) : (
          grouped.map((group) => (
            <div key={group.productId ?? group.productLabel} className="rounded-lg border border-border bg-surface">
              <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
                <span className="text-sm font-medium text-fg">
                  {group.productId ? (
                    <Link className="text-accent hover:underline" to={`/catalog/products/${group.productId}`}>
                      {group.productLabel}
                    </Link>
                  ) : (
                    group.productLabel
                  )}
                </span>
                <Badge tone="neutral">{group.rows.length} waiting</Badge>
              </div>
              <ul className="flex flex-col">
                {group.rows.map((row) => (
                  <li
                    key={row.id}
                    className="flex flex-wrap items-start justify-between gap-3 border-b border-border/60 px-3 py-2.5 last:border-0"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={statusTone(row.status)}>{row.status}</Badge>
                        <span className="text-sm text-fg">
                          {row.customer_label ?? 'Customer'}
                        </span>
                        {row.requested_variant_label ? (
                          <span className="text-xs text-muted">· {row.requested_variant_label}</span>
                        ) : null}
                      </div>
                      <pre className="mt-2 whitespace-pre-wrap rounded-md bg-surface-sunken px-3 py-2 text-xs text-fg">
                        {row.suggested_message}
                      </pre>
                    </div>
                    <div className="flex shrink-0 flex-wrap items-center gap-2">
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          copyToClipboard(row.suggested_message);
                          setCopiedId(row.id);
                          window.setTimeout(() => setCopiedId((current) => (current === row.id ? null : current)), 1500);
                        }}
                      >
                        {copiedId === row.id ? 'Copied' : 'Copy'}
                      </Button>
                      {row.conversation_id ? (
                        <Link
                          className="inline-flex h-8 items-center rounded-lg border border-border bg-surface px-3 text-xs font-medium text-accent hover:bg-surface-sunken"
                          to={`/inbox/${row.conversation_id}`}
                        >
                          Open →
                        </Link>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))
        )}
      </CardBody>
    </Card>
  );
}
