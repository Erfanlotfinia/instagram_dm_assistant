import { useForm } from 'react-hook-form';

import type { CustomerProfile, CustomerUpdate, PreviousOrderSummary } from '../../types/conversation';

interface CustomerProfilePanelProps {
  profile: CustomerProfile | null | undefined;
  onSave: (values: CustomerUpdate) => void;
  isSaving?: boolean;
}

// Map common color names to a displayable swatch color. Standard CSS color
// names render directly; anything unknown falls back to a neutral chip.
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

function orderStatusTone(order: PreviousOrderSummary): string {
  if (order.payment_status === 'paid') return 'status-pill--success';
  if (order.status === 'cancelled') return 'status-pill--danger';
  return 'status-pill--warning';
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
    return <p className="empty-state">No customer profile available.</p>;
  }

  const displayName = profile.full_name?.trim() || profile.instagram_user_id || 'Unknown customer';

  return (
    <div className="customer-profile-panel">
      <header className="cp-header">
        <div className="cp-header__avatar" aria-hidden="true">
          {customerInitial(profile)}
        </div>
        <div className="cp-header__identity">
          <p className="cp-header__name">{displayName}</p>
          {profile.instagram_user_id ? (
            <p className="cp-header__handle">@{profile.instagram_user_id}</p>
          ) : null}
        </div>
        {profile.is_repeat_customer ? (
          <span className="cp-vip-badge" title="Repeat customer">
            ★ VIP
          </span>
        ) : null}
      </header>

      <div className="cp-stats">
        <p className="cp-stat">
          <span className="cp-stat__label">Orders:</span>
          <span className="cp-stat__value">{profile.order_count}</span>
        </p>
        <p className="cp-stat">
          <span className="cp-stat__label">Total paid:</span>
          <span className="cp-stat__value">{profile.total_paid_amount}</span>
        </p>
        <p className="cp-stat">
          <span className="cp-stat__label">Last purchase:</span>
          <span className="cp-stat__value cp-stat__value--sm">{formatDate(profile.last_purchase_at)}</span>
        </p>
      </div>

      <section className="cp-section">
        <h3 className="cp-section__title">Preferences</h3>
        <div className="cp-facts">
          <p className="cp-fact">
            <span className="cp-fact__label">Preferred size:</span>
            <span className="cp-fact__value">{profile.preferred_size ?? '—'}</span>
          </p>
          <p className="cp-fact">
            <span className="cp-fact__label">Previous successful size:</span>
            <span className="cp-fact__value">{profile.last_successful_size ?? '—'}</span>
          </p>
          <div className="cp-fact cp-fact--colors">
            <span className="cp-fact__label">Preferred colors:</span>
            {profile.preferred_colors.length ? (
              <span className="cp-colors">
                <span className="cp-colors__swatches" aria-hidden="true">
                  {profile.preferred_colors.map((color, index) => (
                    <span
                      key={`${color}-${index}`}
                      className="cp-colors__swatch"
                      style={{ background: swatchColor(color) ?? '#cbd2e0' }}
                    />
                  ))}
                </span>
                <span className="cp-colors__names">{profile.preferred_colors.join(', ')}</span>
              </span>
            ) : (
              <span className="cp-fact__value">—</span>
            )}
          </div>
        </div>
      </section>

      <section className="cp-section">
        <h3 className="cp-section__title">
          Order history
          {profile.previous_orders.length > 0 ? (
            <span className="cp-section__count">{profile.previous_orders.length}</span>
          ) : null}
        </h3>
        {profile.previous_orders.length > 0 ? (
          <ul className="cp-orders">
            {profile.previous_orders.map((order) => (
              <li key={order.id} className="cp-order">
                <div className="cp-order__top">
                  <span className="cp-order__id">#{order.id.slice(0, 8)}</span>
                  <span className="cp-order__amount">{order.total_amount}</span>
                </div>
                <div className="cp-order__pills">
                  <span className="status-pill status-pill--neutral">{order.status.replace(/_/g, ' ')}</span>
                  <span className={`status-pill ${orderStatusTone(order)}`}>
                    {order.payment_status.replace(/_/g, ' ')}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="empty-state">No previous orders.</p>
        )}
      </section>

      <section className="cp-section">
        <h3 className="cp-section__title">Edit details</h3>
        <form className="inline-form cp-form" onSubmit={form.handleSubmit(onSave)}>
          <div className="filter-grid">
            <label className="form-field">
              <span>Full name</span>
              <input {...form.register('full_name')} />
            </label>
            <label className="form-field">
              <span>Phone</span>
              <input {...form.register('phone')} />
            </label>
            <label className="form-field">
              <span>City</span>
              <input {...form.register('city')} />
            </label>
            <label className="form-field">
              <span>Postal code</span>
              <input {...form.register('postal_code')} />
            </label>
          </div>
          <label className="form-field">
            <span>Address</span>
            <textarea rows={2} {...form.register('address')} />
          </label>
          <label className="form-field">
            <span>Notes</span>
            <textarea rows={2} {...form.register('notes')} />
          </label>
          <button className="button button--primary" type="submit" disabled={isSaving}>
            {isSaving ? 'Saving…' : 'Save customer'}
          </button>
        </form>
      </section>
    </div>
  );
}
