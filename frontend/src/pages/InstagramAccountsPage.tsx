import { FormEvent, useEffect, useState } from 'react';

import { apiClient } from '../services/apiClient';
import type { InstagramAccount } from '../types/instagramAccount';
import type { Shop } from '../types/shop';

export function InstagramAccountsPage() {
  const [shops, setShops] = useState<Shop[]>([]);
  const [selectedShopId, setSelectedShopId] = useState('');
  const [accounts, setAccounts] = useState<InstagramAccount[]>([]);
  const [username, setUsername] = useState('');
  const [igUserId, setIgUserId] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    apiClient
      .listShops()
      .then((data) => {
        setShops(data);
        if (data.length > 0) {
          setSelectedShopId(data[0].id);
        }
      })
      .catch(() => setShops([]));
  }, []);

  useEffect(() => {
    if (!selectedShopId) {
      setAccounts([]);
      return;
    }

    apiClient
      .listInstagramAccounts(selectedShopId)
      .then(setAccounts)
      .catch(() => setAccounts([]));
  }, [selectedShopId]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedShopId) {
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await apiClient.createInstagramAccount(selectedShopId, {
        ig_user_id: igUserId,
        username,
        access_token: accessToken,
      });
      setUsername('');
      setIgUserId('');
      setAccessToken('');
      const updated = await apiClient.listInstagramAccounts(selectedShopId);
      setAccounts(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect account');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="dashboard-card">
        <p className="dashboard-card__eyebrow">Instagram</p>
        <h1>Instagram accounts</h1>
        <p>Connect Instagram business accounts to shops for DM automation.</p>

        <label className="form-field">
          <span>Shop</span>
          <select value={selectedShopId} onChange={(event) => setSelectedShopId(event.target.value)}>
            <option value="">Select a shop</option>
            {shops.map((shop) => (
              <option key={shop.id} value={shop.id}>
                {shop.name}
              </option>
            ))}
          </select>
        </label>

        <form className="inline-form" onSubmit={handleCreate}>
          <label className="form-field">
            <span>Instagram user ID</span>
            <input value={igUserId} onChange={(event) => setIgUserId(event.target.value)} required />
          </label>
          <label className="form-field">
            <span>Username</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} required />
          </label>
          <label className="form-field">
            <span>Access token</span>
            <input
              type="password"
              value={accessToken}
              onChange={(event) => setAccessToken(event.target.value)}
              required
            />
          </label>
          <button
            className="button button--primary"
            type="submit"
            disabled={isSubmitting || !selectedShopId}
          >
            {isSubmitting ? 'Connecting...' : 'Connect account'}
          </button>
        </form>
        {error ? <p className="form-error">{error}</p> : null}
      </section>

      <section className="dashboard-card">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>IG user ID</th>
                <th>Status</th>
                <th>Webhook</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((account) => (
                <tr key={account.id}>
                  <td>{account.username}</td>
                  <td>{account.ig_user_id}</td>
                  <td>{account.status}</td>
                  <td>{account.webhook_enabled ? 'enabled' : 'disabled'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {accounts.length === 0 ? <p className="empty-state">No Instagram accounts connected.</p> : null}
        </div>
      </section>
    </div>
  );
}
