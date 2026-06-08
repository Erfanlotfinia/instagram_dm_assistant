import { useForm } from 'react-hook-form';

import type { CustomerProfile, CustomerUpdate } from '../../types/conversation';

interface CustomerProfilePanelProps {
  profile: CustomerProfile | null | undefined;
  onSave: (values: CustomerUpdate) => void;
  isSaving?: boolean;
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

  return (
    <div className="customer-profile-panel">
      <div className="detail-grid">
        <p>
          <strong>Orders:</strong> {profile.order_count}
        </p>
        <p>
          <strong>Total paid:</strong> {profile.total_paid_amount}
        </p>
        <p>
          <strong>Last purchase:</strong>{' '}
          {profile.last_purchase_at ? new Date(profile.last_purchase_at).toLocaleDateString() : '—'}
        </p>
        <p>
          <strong>Preferred size:</strong> {profile.preferred_size ?? '—'}
        </p>
        <p>
          <strong>Preferred colors:</strong>{' '}
          {profile.preferred_colors.length ? profile.preferred_colors.join(', ') : '—'}
        </p>
        {profile.is_repeat_customer ? <span className="status-pill">VIP / repeat</span> : null}
      </div>

      {profile.previous_orders.length > 0 ? (
        <ul className="simple-list">
          {profile.previous_orders.map((order) => (
            <li key={order.id}>
              {order.id.slice(0, 8)} · {order.status} · {order.payment_status} ·{' '}
              {order.total_amount}
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty-state">No previous orders.</p>
      )}

      <form className="inline-form" onSubmit={form.handleSubmit(onSave)}>
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
          Save customer
        </button>
      </form>
    </div>
  );
}
