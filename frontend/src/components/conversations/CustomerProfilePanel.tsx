import { useForm } from 'react-hook-form';

import { EmptyState } from '../data';
import { Badge, Button, Field, Input, type BadgeTone } from '../ui';
import type { CustomerProfile, CustomerUpdate, PreviousOrderSummary } from '../../types/conversation';
import { cn } from '../../lib/cn';

/*
 * Catalog product color swatches below use dynamic `style.background` from customer
 * profile data — a narrow, documented exception to the Modira-only UI palette rule.
 */

interface CustomerProfilePanelProps {
  profile: CustomerProfile | null | undefined;
  onSave: (values: CustomerUpdate) => void;
  isSaving?: boolean;
}

const KNOWN_CSS_COLORS = new Set([
  'black', 'white', 'red', 'green', 'blue', 'navy', 'gray', 'grey', 'silver',
  'maroon', 'olive', 'lime', 'aqua', 'teal', 'fuchsia', 'purple', 'pink',
  'orange', 'yellow', 'brown', 'beige', 'gold', 'ivory', 'khaki', 'coral',
  'crimson', 'cyan', 'magenta', 'indigo', 'violet', 'tan', 'turquoise',
]);

function swatchColor(name: string): string | undefined {
  const normalized = name.trim().toLowerCase();
  return KNOWN_CSS_COLORS.has(normalized) ? normalized : undefined;
}

function customerInitial(profile: CustomerProfile): string {
  const source = profile.full_name?.trim() || profile.instagram_user_id || '?';
  return source.charAt(0).toUpperCase();
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleDateString();
}

function paymentTone(order: PreviousOrderSummary): BadgeTone {
  if (order.payment_status === 'paid') return 'success';
  if (order.status === 'cancelled') return 'danger';
  return 'warning';
}

export function CustomerProfilePanel({ profile, onSave, isSaving }: CustomerProfilePanelProps) {
  const form = useForm<CustomerUpdate>({
    values: {
      full_name: profile?.full_name ?? '',
      phone: profile?.phone ?? '',
      city: profile?.city ?? '',
      address: profile?.address ?? '',
      postal_code: profile?.postal_code ?? '',
      notes: profile?.notes ?? '',
    },
  });

  if (!profile) {
    return <EmptyState title="No customer profile available" />;
  }

  const displayName = profile.full_name?.trim() || profile.instagram_user_id || 'Unknown customer';

  return (
    <div className="flex flex-col gap-4">
      <header className="flex items-start gap-3">
        <div
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent"
          aria-hidden="true"
        >
          {customerInitial(profile)}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold text-fg">{displayName}</p>
          {profile.instagram_user_id ? (
            <p className="truncate text-sm text-muted">@{profile.instagram_user_id}</p>
          ) : null}
        </div>
        {profile.is_repeat_customer ? (
          <Badge tone="accent" title="Repeat customer">
            ★ VIP
          </Badge>
        ) : null}
      </header>

      <dl className="grid gap-2 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-muted">Orders</dt>
          <dd className="font-medium text-fg">{profile.order_count}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Total paid</dt>
          <dd className="font-medium text-fg">{profile.total_paid_amount}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Last purchase</dt>
          <dd className="text-fg">{formatDate(profile.last_purchase_at)}</dd>
        </div>
      </dl>

      <section className="flex flex-col gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Preferences</h3>
        <dl className="grid gap-2 text-sm">
          <div className="flex justify-between gap-2">
            <dt className="text-muted">Preferred size</dt>
            <dd className="text-fg">{profile.preferred_size ?? '—'}</dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt className="text-muted">Previous successful size</dt>
            <dd className="text-fg">{profile.last_successful_size ?? '—'}</dd>
          </div>
          <div className="flex flex-col gap-1">
            <dt className="text-muted">Preferred colors</dt>
            <dd>
              {profile.preferred_colors.length ? (
                <span className="inline-flex flex-wrap items-center gap-2">
                  <span className="inline-flex gap-1" aria-hidden="true">
                    {profile.preferred_colors.map((color, index) => (
                      <span
                        key={`${color}-${index}`}
                        className="h-4 w-4 rounded-full border border-border"
                        style={{ background: swatchColor(color) ?? 'var(--c-border)' }}
                      />
                    ))}
                  </span>
                  <span className="text-fg">{profile.preferred_colors.join(', ')}</span>
                </span>
              ) : (
                '—'
              )}
            </dd>
          </div>
        </dl>
      </section>

      <section className="flex flex-col gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">
          Order history
          {profile.previous_orders.length > 0 ? (
            <span className="ml-1.5 rounded-full bg-surface-sunken px-1.5 py-0.5 text-[10px] font-medium text-muted">
              {profile.previous_orders.length}
            </span>
          ) : null}
        </h3>
        {profile.previous_orders.length > 0 ? (
          <ul className="space-y-2">
            {profile.previous_orders.map((order) => (
              <li key={order.id} className="rounded-lg border border-border bg-surface-sunken p-2.5">
                <div className="flex items-center justify-between gap-2 text-sm">
                  <span className="font-mono text-xs text-muted">#{order.id.slice(0, 8)}</span>
                  <span className="font-medium text-fg">{order.total_amount}</span>
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  <Badge tone="neutral">{order.status.replace(/_/g, ' ')}</Badge>
                  <Badge tone={paymentTone(order)}>{order.payment_status.replace(/_/g, ' ')}</Badge>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="No previous orders" />
        )}
      </section>

      <section className="flex flex-col gap-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">Edit details</h3>
        <form className="flex flex-col gap-3" onSubmit={form.handleSubmit(onSave)}>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Full name" htmlFor="customer-full-name">
              <Input id="customer-full-name" {...form.register('full_name')} />
            </Field>
            <Field label="Phone" htmlFor="customer-phone">
              <Input id="customer-phone" {...form.register('phone')} />
            </Field>
            <Field label="City" htmlFor="customer-city">
              <Input id="customer-city" {...form.register('city')} />
            </Field>
            <Field label="Postal code" htmlFor="customer-postal">
              <Input id="customer-postal" {...form.register('postal_code')} />
            </Field>
          </div>
          <Field label="Address" htmlFor="customer-address">
            <textarea
              id="customer-address"
              rows={2}
              {...form.register('address')}
              className={cn(
                'w-full resize-y rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg',
                'placeholder:text-subtle focus:border-accent focus:outline-none',
              )}
            />
          </Field>
          <Field label="Notes" htmlFor="customer-notes">
            <textarea
              id="customer-notes"
              rows={2}
              {...form.register('notes')}
              className={cn(
                'w-full resize-y rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg',
                'placeholder:text-subtle focus:border-accent focus:outline-none',
              )}
            />
          </Field>
          <Button type="submit" size="sm" disabled={isSaving}>
            {isSaving ? 'Saving…' : 'Save customer'}
          </Button>
        </form>
      </section>
    </div>
  );
}
