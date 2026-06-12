import { FormEvent, useEffect, useMemo, useState } from 'react';

import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';
import type { ChannelAccount, ChannelProvider } from '../types/channel';

const PROVIDERS: Array<{ value: ChannelProvider; label: string; hint: string }> = [
  { value: 'instagram', label: 'Instagram', hint: 'Meta webhook signature and Instagram Graph send APIs.' },
  { value: 'whatsapp', label: 'WhatsApp', hint: 'Cloud API phone number ID, verify token, templates and 24h service window.' },
  { value: 'telegram', label: 'Telegram', hint: 'Bot API token with optional X-Telegram-Bot-Api-Secret-Token webhook header.' },
  { value: 'bale', label: 'Bale', hint: 'Telegram-like bot endpoint with Bale token and webhook limits.' },
  { value: 'rubika', label: 'Rubika', hint: 'HTTPS endpoint mode, receiveUpdate and receiveInlineMessage support.' },
];

function providerLabel(provider: ChannelProvider) {
  return PROVIDERS.find((item) => item.value === provider)?.label ?? provider;
}

export function ChannelAccountsPage() {
  const { selectedShopId, selectedShop } = useShop();
  const [accounts, setAccounts] = useState<ChannelAccount[]>([]);
  const [provider, setProvider] = useState<ChannelProvider>('instagram');
  const [displayName, setDisplayName] = useState('');
  const [externalAccountId, setExternalAccountId] = useState('');
  const [phoneNumberId, setPhoneNumberId] = useState('');
  const [botUsername, setBotUsername] = useState('');
  const [botId, setBotId] = useState('');
  const [webhookVerifyToken, setWebhookVerifyToken] = useState('');
  const [webhookSecret, setWebhookSecret] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [botToken, setBotToken] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedProvider = useMemo(() => PROVIDERS.find((item) => item.value === provider)!, [provider]);

  async function loadAccounts() {
    if (!selectedShopId) {
      setAccounts([]);
      return;
    }
    setIsLoading(true);
    try {
      setAccounts(await apiClient.listChannelAccounts(selectedShopId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load channel accounts');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadAccounts();
  }, [selectedShopId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedShopId) return;
    setError(null);
    try {
      await apiClient.createChannelAccount(selectedShopId, {
        provider,
        display_name: displayName,
        external_account_id: externalAccountId || undefined,
        phone_number_id: phoneNumberId || undefined,
        bot_username: botUsername || undefined,
        bot_id: botId || undefined,
        webhook_verify_token: webhookVerifyToken || undefined,
        webhook_secret: webhookSecret || undefined,
        access_token: accessToken || undefined,
        bot_token: botToken || undefined,
      });
      setDisplayName('');
      setExternalAccountId('');
      setPhoneNumberId('');
      setBotUsername('');
      setBotId('');
      setWebhookVerifyToken('');
      setWebhookSecret('');
      setAccessToken('');
      setBotToken('');
      await loadAccounts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create channel account');
    }
  }

  async function handleWebhookTest(account: ChannelAccount) {
    if (!selectedShopId) return;
    setError(null);
    try {
      await apiClient.testChannelWebhook(selectedShopId, account.id);
      window.alert(`${providerLabel(account.provider)} webhook test accepted`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Webhook test failed');
    }
  }

  return (
    <div className="page-stack">
      <section className="dashboard-card">
        <p className="dashboard-card__eyebrow">Multi-channel</p>
        <h1>Channel Accounts</h1>
        <p>Connect Instagram, WhatsApp, Telegram, Bale and Rubika to the same normalized order pipeline for {selectedShop?.name ?? 'your shop'}.</p>
        {error && <div className="alert alert--error">{error}</div>}
      </section>

      <section className="dashboard-card">
        <h2>Add channel account</h2>
        <form className="form-grid" onSubmit={handleSubmit}>
          <label className="form-field">
            <span>Provider</span>
            <select value={provider} onChange={(event) => setProvider(event.target.value as ChannelProvider)}>
              {PROVIDERS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
            <small>{selectedProvider.hint}</small>
          </label>
          <label className="form-field"><span>Display name</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} required /></label>
          {(provider === 'instagram' || provider === 'whatsapp') && <label className="form-field"><span>External account ID</span><input value={externalAccountId} onChange={(event) => setExternalAccountId(event.target.value)} /></label>}
          {provider === 'whatsapp' && <label className="form-field"><span>Phone number ID</span><input value={phoneNumberId} onChange={(event) => setPhoneNumberId(event.target.value)} required /></label>}
          {provider !== 'instagram' && provider !== 'whatsapp' && <label className="form-field"><span>Bot username</span><input value={botUsername} onChange={(event) => setBotUsername(event.target.value)} /></label>}
          {provider !== 'instagram' && provider !== 'whatsapp' && <label className="form-field"><span>Bot ID</span><input value={botId} onChange={(event) => setBotId(event.target.value)} /></label>}
          <label className="form-field"><span>Webhook verify token</span><input value={webhookVerifyToken} onChange={(event) => setWebhookVerifyToken(event.target.value)} /></label>
          <label className="form-field"><span>Webhook secret</span><input type="password" value={webhookSecret} onChange={(event) => setWebhookSecret(event.target.value)} /></label>
          {(provider === 'instagram' || provider === 'whatsapp') && <label className="form-field"><span>Access token</span><input type="password" value={accessToken} onChange={(event) => setAccessToken(event.target.value)} /></label>}
          {provider !== 'instagram' && <label className="form-field"><span>Bot token</span><input type="password" value={botToken} onChange={(event) => setBotToken(event.target.value)} /></label>}
          <button className="button button--primary" type="submit" disabled={!selectedShopId}>Add channel</button>
        </form>
      </section>

      <section className="dashboard-card">
        <h2>Connected channels</h2>
        {isLoading && <p>Loading channel accounts…</p>}
        {!isLoading && accounts.length === 0 && <p>No channel accounts connected yet.</p>}
        {accounts.length > 0 && (
          <div className="table-card"><table><thead><tr><th>Provider</th><th>Name</th><th>Status</th><th>External ID</th><th>Capabilities</th><th>Webhook</th></tr></thead><tbody>
            {accounts.map((account) => (
              <tr key={account.id}>
                <td><span className="status-pill">{providerLabel(account.provider)}</span></td>
                <td>{account.display_name}</td>
                <td>{account.status}</td>
                <td>{account.external_account_id ?? account.phone_number_id ?? account.bot_id ?? '—'}</td>
                <td>{Object.entries(account.capabilities_json).filter(([, enabled]) => enabled === true).slice(0, 4).map(([key]) => key.replace('supports_', '')).join(', ') || '—'}</td>
                <td><button className="button button--secondary" type="button" onClick={() => void handleWebhookTest(account)}>Webhook test</button></td>
              </tr>
            ))}
          </tbody></table></div>
        )}
      </section>
    </div>
  );
}
