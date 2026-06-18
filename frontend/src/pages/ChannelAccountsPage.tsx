import { FormEvent, useEffect, useMemo, useState } from 'react';

import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input, Select } from '../components/ui';
import { DataTable, EmptyState, LoadingState } from '../components/data';
import type { Column } from '../components/data';
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
  const [defaultLanguageCode, setDefaultLanguageCode] = useState('en_US');
  const [webhookInfo, setWebhookInfo] = useState<unknown | null>(null);
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
      const account = await apiClient.createChannelAccount(selectedShopId, {
        provider,
        display_name: displayName,
        external_account_id: externalAccountId || undefined,
        phone_number_id: phoneNumberId || undefined,
        bot_username: botUsername || undefined,
        bot_id: botId || undefined,
        webhook_verify_token: webhookVerifyToken || undefined,
        settings: {
          ...(provider === 'telegram' ? { allowed_updates_json: ['message', 'callback_query'], use_local_bot_api: false } : {}),
          ...(provider === 'whatsapp' ? { message_template_namespace: null, default_language_code: defaultLanguageCode } : {}),
        },
      });
      await apiClient.updateChannelCredentials(selectedShopId, account.id, {
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
      setDefaultLanguageCode('en_US');
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

  async function handleTelegramWebhookInfo(account: ChannelAccount) {
    if (!selectedShopId) return;
    setError(null);
    try {
      setWebhookInfo(await apiClient.getTelegramWebhookInfo(selectedShopId, account.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Webhook info failed');
    }
  }

  async function handleSetTelegramWebhook(account: ChannelAccount) {
    if (!selectedShopId) return;
    setError(null);
    try {
      setWebhookInfo(await apiClient.setTelegramWebhook(selectedShopId, account.id));
      await loadAccounts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Set webhook failed');
    }
  }

  async function handleDeleteTelegramWebhook(account: ChannelAccount) {
    if (!selectedShopId) return;
    setError(null);
    try {
      setWebhookInfo(await apiClient.deleteTelegramWebhook(selectedShopId, account.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete webhook failed');
    }
  }

  const accountColumns: Column<ChannelAccount>[] = [
    {
      key: 'provider',
      header: 'Provider',
      render: (account) => <Badge tone="neutral">{providerLabel(account.provider)}</Badge>,
    },
    { key: 'name', header: 'Name', render: (account) => account.display_name },
    { key: 'status', header: 'Status', render: (account) => <Badge tone="neutral">{account.status}</Badge> },
    {
      key: 'external',
      header: 'External ID',
      render: (account) => account.external_account_id ?? account.phone_number_id ?? account.bot_id ?? '—',
    },
    {
      key: 'capabilities',
      header: 'Capabilities',
      render: (account) =>
        Object.entries(account.capabilities_json)
          .filter(([, enabled]) => enabled === true)
          .slice(0, 4)
          .map(([key]) => key.replace('supports_', ''))
          .join(', ') || '—',
    },
    {
      key: 'webhook',
      header: 'Webhook',
      render: (account) => (
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="secondary" size="sm" onClick={() => void handleWebhookTest(account)}>
            Webhook test
          </Button>
          {account.provider === 'telegram' ? (
            <>
              <Button type="button" variant="secondary" size="sm" onClick={() => void handleSetTelegramWebhook(account)}>
                Set webhook
              </Button>
              <Button type="button" variant="secondary" size="sm" onClick={() => void handleDeleteTelegramWebhook(account)}>
                Delete webhook
              </Button>
              <Button type="button" variant="secondary" size="sm" onClick={() => void handleTelegramWebhookInfo(account)}>
                Webhook info
              </Button>
            </>
          ) : null}
          {account.provider === 'whatsapp' ? (
            <Badge tone="warning">Template picker enabled outside window</Badge>
          ) : null}
        </div>
      ),
    },
  ];

  return (
    <HubPage
      eyebrow="Multi-channel"
      title="Channel Accounts"
      description={`Connect Instagram, WhatsApp, Telegram, Bale and Rubika to the same normalized order pipeline for ${selectedShop?.name ?? 'your shop'}.`}
    >
      {error ? (
        <Card>
          <CardBody>
            <p className="text-sm text-danger">{error}</p>
          </CardBody>
        </Card>
      ) : null}

      {!selectedShopId ? (
        <Card>
          <CardBody>
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          </CardBody>
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader title="Add channel account" />
            <CardBody>
              <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleSubmit}>
                <Field label="Provider" hint={selectedProvider.hint}>
                  <Select value={provider} onChange={(event) => setProvider(event.target.value as ChannelProvider)}>
                    {PROVIDERS.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Display name">
                  <Input value={displayName} onChange={(event) => setDisplayName(event.target.value)} required />
                </Field>
                {(provider === 'instagram' || provider === 'whatsapp') && (
                  <Field label="External account ID">
                    <Input value={externalAccountId} onChange={(event) => setExternalAccountId(event.target.value)} />
                  </Field>
                )}
                {provider === 'whatsapp' && (
                  <Field label="Phone number ID">
                    <Input value={phoneNumberId} onChange={(event) => setPhoneNumberId(event.target.value)} required />
                  </Field>
                )}
                {provider === 'whatsapp' && (
                  <Field label="Business account ID">
                    <Input
                      value={externalAccountId}
                      onChange={(event) => setExternalAccountId(event.target.value)}
                      placeholder="Optional WABA ID"
                    />
                  </Field>
                )}
                {provider === 'whatsapp' && (
                  <Field label="Default language">
                    <Input
                      value={defaultLanguageCode}
                      onChange={(event) => setDefaultLanguageCode(event.target.value)}
                      placeholder="en_US"
                    />
                  </Field>
                )}
                {provider !== 'instagram' && provider !== 'whatsapp' && (
                  <Field label="Bot username">
                    <Input value={botUsername} onChange={(event) => setBotUsername(event.target.value)} />
                  </Field>
                )}
                {provider !== 'instagram' && provider !== 'whatsapp' && (
                  <Field label="Bot ID">
                    <Input value={botId} onChange={(event) => setBotId(event.target.value)} />
                  </Field>
                )}
                <Field label="Webhook verify token">
                  <Input value={webhookVerifyToken} onChange={(event) => setWebhookVerifyToken(event.target.value)} />
                </Field>
                <Field label={provider === 'whatsapp' ? 'App secret' : 'Webhook secret token'}>
                  <Input type="password" value={webhookSecret} onChange={(event) => setWebhookSecret(event.target.value)} />
                </Field>
                {(provider === 'instagram' || provider === 'whatsapp') && (
                  <Field label="Access token">
                    <Input type="password" value={accessToken} onChange={(event) => setAccessToken(event.target.value)} />
                  </Field>
                )}
                {provider !== 'instagram' && (
                  <Field label="Bot token">
                    <Input type="password" value={botToken} onChange={(event) => setBotToken(event.target.value)} />
                  </Field>
                )}
                <div className="flex items-end sm:col-span-2">
                  <Button type="submit" disabled={!selectedShopId}>
                    Add channel
                  </Button>
                </div>
              </form>
              {provider === 'whatsapp' ? (
                <div className="mt-4 rounded-lg border border-info/30 bg-info-soft/30 px-4 py-3 text-sm text-fg">
                  Configure Meta webhook URL <code className="text-xs">/api/v1/channels/whatsapp/webhook</code>; use the
                  verify token above and keep App Secret set in staging/production for X-Hub-Signature-256 validation. Use
                  approved templates outside the 24-hour customer service window.
                </div>
              ) : null}
              {provider === 'telegram' ? (
                <div className="mt-4 rounded-lg border border-info/30 bg-info-soft/30 px-4 py-3 text-sm text-fg">
                  Configure Telegram webhook URL <code className="text-xs">/api/v1/channels/telegram/webhook</code>. If a
                  secret token is set via setWebhook, Telegram sends it in{' '}
                  <code className="text-xs">X-Telegram-Bot-Api-Secret-Token</code>.
                </div>
              ) : null}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Connected channels" />
            {isLoading ? (
              <CardBody>
                <LoadingState label="Loading channel accounts…" />
              </CardBody>
            ) : (
              <DataTable
                columns={accountColumns}
                rows={accounts}
                rowKey={(account) => account.id}
                emptyTitle="No channel accounts connected yet"
              />
            )}
          </Card>

          <Card>
            <CardHeader
              title="WhatsApp Templates"
              description="Create local template records in this sprint through the backend model. Sync with Meta Template APIs is prepared as a provider limitation until template-management credentials are enabled."
            />
            <CardBody className="flex flex-col gap-3">
              <div className="flex flex-wrap gap-2">
                <Badge tone="success">approved</Badge>
                <Badge tone="warning">submitted</Badge>
                <Badge tone="danger">rejected</Badge>
              </div>
              <p className="text-sm text-muted">
                <strong className="text-fg">Filters:</strong> language, category and status are supported by the template
                data model.
              </p>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Telegram webhook info panel" />
            <CardBody>
              {webhookInfo ? (
                <pre className="max-h-96 overflow-auto rounded-md bg-surface-sunken p-3 text-xs text-subtle">
                  {JSON.stringify(webhookInfo, null, 2)}
                </pre>
              ) : (
                <EmptyState
                  title="No webhook info loaded"
                  description="Select Webhook info on a Telegram account to inspect Telegram's current webhook state."
                />
              )}
            </CardBody>
          </Card>
        </>
      )}
    </HubPage>
  );
}
