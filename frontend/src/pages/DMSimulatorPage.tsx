import { FormEvent, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';

export function DMSimulatorPage() {
  const { selectedShopId } = useShop();
  const [instagramAccountId, setInstagramAccountId] = useState('');
  const [messageText, setMessageText] = useState('این کارو مشکی سایز L می‌خوام');
  const [postUrl, setPostUrl] = useState('');
  const accountsQuery = useQuery({
    queryKey: ['instagram-accounts', selectedShopId],
    queryFn: () => apiClient.listInstagramAccounts(selectedShopId),
    enabled: Boolean(selectedShopId),
  });
  const runMutation = useMutation({
    mutationFn: () => apiClient.runDMSimulator(selectedShopId, {
      instagram_account_id: instagramAccountId || accountsQuery.data?.[0]?.id || '',
      message_text: messageText,
      shared_post_url: postUrl || null,
    }),
  });
  const resetMutation = useMutation({ mutationFn: () => apiClient.resetDMSimulator(selectedShopId) });
  function submit(event: FormEvent) {
    event.preventDefault();
    runMutation.mutate();
  }
  const result = runMutation.data;
  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Safe test mode</p>
        <h1>DM Simulator</h1>
        <p>Runs through the production orchestrator but never sends a real Instagram message.</p>
        <ShopSelector />
      </section>
      <section className="dashboard-card dashboard-card--wide">
        <form className="form-grid" onSubmit={submit}>
          <label>Instagram account
            <select value={instagramAccountId} onChange={(e) => setInstagramAccountId(e.target.value)}>
              <option value="">Select account</option>
              {accountsQuery.data?.map((account) => <option key={account.id} value={account.id}>@{account.username}</option>)}
            </select>
          </label>
          <label>Fake customer message
            <textarea value={messageText} onChange={(e) => setMessageText(e.target.value)} />
          </label>
          <label>Shared Instagram post URL (optional)
            <input value={postUrl} onChange={(e) => setPostUrl(e.target.value)} />
          </label>
          <button type="submit" disabled={runMutation.isPending}>Run simulator</button>
          <button type="button" onClick={() => resetMutation.mutate()}>Reset simulation data</button>
        </form>
      </section>
      {result ? (
        <section className="dashboard-card dashboard-card--wide">
          <h2>Simulation result</h2>
          <div className="stats-grid">
            <article className="stat-card"><p className="stat-card__label">Intent</p><p className="stat-card__value">{result.extracted_intent ?? '—'}</p></article>
            <article className="stat-card"><p className="stat-card__label">Next state</p><p className="stat-card__value">{result.next_state}</p></article>
            <article className="stat-card"><p className="stat-card__label">Preview</p><p className="stat-card__value">{result.preview_required ? 'Required' : 'No'}</p></article>
            <article className="stat-card"><p className="stat-card__label">Handoff</p><p className="stat-card__value">{result.handoff_required ? 'Yes' : 'No'}</p></article>
          </div>
          <h3>Suggested reply</h3>
          <p className="empty-state">{result.suggested_reply ?? 'No reply generated'}</p>
          <pre>{JSON.stringify({ slots: result.extracted_slots, product: result.product_resolution, variant: result.variant_resolution, inventory: result.inventory_result }, null, 2)}</pre>
        </section>
      ) : null}
    </div>
  );
}
