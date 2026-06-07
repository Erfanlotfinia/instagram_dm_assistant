import { FormEvent, useEffect, useState } from 'react';

import { apiClient } from '../services/apiClient';
import type { Shop } from '../types/shop';

export function ShopsPage() {
  const [shops, setShops] = useState<Shop[]>([]);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function loadShops() {
    const data = await apiClient.listShops();
    setShops(data);
  }

  useEffect(() => {
    loadShops().catch(() => setShops([]));
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await apiClient.createShop({
        name,
        slug: slug || undefined,
      });
      setName('');
      setSlug('');
      await loadShops();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create shop');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="dashboard-card">
        <p className="dashboard-card__eyebrow">Shops</p>
        <h1>Your shops</h1>
        <p>Manage the shops you belong to and create new storefronts.</p>

        <form className="inline-form" onSubmit={handleCreate}>
          <label className="form-field">
            <span>Name</span>
            <input value={name} onChange={(event) => setName(event.target.value)} required />
          </label>
          <label className="form-field">
            <span>Slug (optional)</span>
            <input value={slug} onChange={(event) => setSlug(event.target.value)} />
          </label>
          <button className="button button--primary" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Creating...' : 'Create shop'}
          </button>
        </form>
        {error ? <p className="form-error">{error}</p> : null}
      </section>

      <section className="dashboard-card">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Slug</th>
                <th>Status</th>
                <th>Currency</th>
              </tr>
            </thead>
            <tbody>
              {shops.map((shop) => (
                <tr key={shop.id}>
                  <td>{shop.name}</td>
                  <td>{shop.slug}</td>
                  <td>{shop.status}</td>
                  <td>{shop.default_currency}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {shops.length === 0 ? <p className="empty-state">No shops yet.</p> : null}
        </div>
      </section>
    </div>
  );
}
