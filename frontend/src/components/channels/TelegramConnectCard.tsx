import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { Badge, Button, Card, CardBody, CardHeader, Field, Input } from '../ui';
import { useToast } from '../../contexts/ToastContext';
import { apiClient } from '../../services/apiClient';
import {
  formatTelegramLastSync,
  formatTelegramRights,
  formatValidationTime,
  getTelegramAccountLabel,
  getWebhookStatusLabel,
  isTelegramBusinessActive,
} from '../../lib/channelAccounts';
import type {
  ChannelAccount,
  TelegramConnectionMode,
  TelegramConnectSession,
} from '../../types/channel';

interface TelegramConnectCardProps {
  shopId: string;
  account: ChannelAccount | null;
  canManage: boolean;
  onRefresh: () => void;
}

const MODE_LABELS: Record<TelegramConnectionMode, string> = {
  bot: 'Classic Bot',
  business: 'Business Account',
  hybrid: 'Hybrid',
};

export function TelegramConnectCard({
  shopId,
  account,
  canManage,
  onRefresh,
}: TelegramConnectCardProps) {
  const { showToast } = useToast();
  const [selectedMode, setSelectedMode] = useState<TelegramConnectionMode>('bot');
  const [session, setSession] = useState<TelegramConnectSession | null>(null);
  const [botToken, setBotToken] = useState('');
  const [webhookSecret, setWebhookSecret] = useState('');
  const [showAdvancedToken, setShowAdvancedToken] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isRotating, setIsRotating] = useState(false);

  const isConnected =
    account !== null &&
    account.status !== 'disabled' &&
    account.status !== 'disconnected' &&
    account.bot_token_configured;

  const businessActive = account ? isTelegramBusinessActive(account) : false;
  const showBusinessPanel =
    account?.connection_mode === 'business' || account?.connection_mode === 'hybrid';
  const isManagedAccount = Boolean(account?.managed_bot);

  useEffect(() => {
    if (!session || session.status === 'failed' || session.status === 'expired') {
      return;
    }
    const timer = window.setInterval(async () => {
      try {
        const updated = await apiClient.getTelegramConnectSession(shopId, session.id);
        setSession(updated);
        if (updated.status === 'connected') {
          const message = updated.managed_bot
            ? 'Telegram bot created and connected.'
            : 'Telegram business connection established.';
          showToast(message, 'success');
          setSession(null);
          onRefresh();
        }
        if (updated.status === 'failed' && updated.error_message) {
          showToast(updated.error_message, 'error');
        }
      } catch {
        // polling errors are non-fatal
      }
    }, 4000);
    return () => window.clearInterval(timer);
  }, [session, shopId, onRefresh, showToast]);

  async function handleCreateManagedBot() {
    setIsConnecting(true);
    try {
      const response = await apiClient.startTelegramConnect(shopId, {
        mode: 'bot',
        display_name: 'Telegram',
        channel_account_id: account?.id,
        managed_bot: true,
      });
      const fullSession = await apiClient.getTelegramConnectSession(shopId, response.session_id);
      setSession(fullSession);
      setSelectedMode('bot');
      setShowAdvancedToken(false);
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Could not start bot creation', 'error');
    } finally {
      setIsConnecting(false);
    }
  }

  async function handleStartConnect(mode: TelegramConnectionMode) {
    setIsConnecting(true);
    try {
      const response = await apiClient.startTelegramConnect(shopId, {
        mode,
        display_name: 'Telegram',
        channel_account_id: account?.id,
      });
      const fullSession = await apiClient.getTelegramConnectSession(shopId, response.session_id);
      setSession(fullSession);
      setSelectedMode(mode);
      setShowAdvancedToken(true);
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Could not start Telegram connect', 'error');
    } finally {
      setIsConnecting(false);
    }
  }

  async function handleSubmitToken(event: FormEvent) {
    event.preventDefault();
    if (!session) {
      return;
    }
    setIsConnecting(true);
    try {
      const updated = await apiClient.submitTelegramBotToken(shopId, session.id, {
        bot_token: botToken,
        webhook_secret: webhookSecret || undefined,
      });
      setSession(updated);
      setBotToken('');
      if (updated.status === 'connected') {
        await apiClient.completeTelegramConnect(shopId, session.id);
        showToast('Telegram connected.', 'success');
        setSession(null);
        onRefresh();
      } else if (updated.status === 'waiting_business_connection') {
        showToast('Bot linked. Connect your business account in Telegram.', 'success');
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Could not save bot token', 'error');
    } finally {
      setIsConnecting(false);
    }
  }

  async function handleDisconnect() {
    if (!account) {
      return;
    }
    setIsDisconnecting(true);
    try {
      await apiClient.disconnectChannel(shopId, account.id);
      showToast('Telegram disconnected.', 'success');
      onRefresh();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Disconnect failed', 'error');
    } finally {
      setIsDisconnecting(false);
    }
  }

  async function handleSync() {
    if (!account) {
      return;
    }
    setIsSyncing(true);
    try {
      await apiClient.refreshTelegramBusiness(shopId, account.id);
      showToast('Telegram business connection refreshed.', 'success');
      onRefresh();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Refresh failed', 'error');
    } finally {
      setIsSyncing(false);
    }
  }

  async function handleRotateToken() {
    if (!account) {
      return;
    }
    if (!window.confirm('Rotate the bot token? The old token will stop working immediately.')) {
      return;
    }
    setIsRotating(true);
    try {
      await apiClient.rotateTelegramManagedBotToken(shopId, account.id);
      showToast('Bot token rotated.', 'success');
      onRefresh();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Token rotation failed', 'error');
    } finally {
      setIsRotating(false);
    }
  }

  async function handleReconnect() {
    if (!account) {
      await handleCreateManagedBot();
      return;
    }
    setIsConnecting(true);
    try {
      if (account.managed_bot) {
        await apiClient.reconnectTelegramManagedBot(shopId, account.id);
        showToast('Telegram bot reconnected.', 'success');
        onRefresh();
        return;
      }
      const response = await apiClient.reconnectTelegramBusiness(shopId, account.id);
      const fullSession = await apiClient.getTelegramConnectSession(shopId, response.session_id);
      setSession(fullSession);
      setSelectedMode(account.connection_mode ?? 'business');
      setShowAdvancedToken(true);
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Could not reconnect', 'error');
    } finally {
      setIsConnecting(false);
    }
  }

  const modeLabel = account?.connection_mode ? MODE_LABELS[account.connection_mode] : undefined;
  const realAccountLabel = account ? getTelegramAccountLabel(account) : null;

  return (
    <Card>
      <CardHeader
        title="Telegram"
        description="Create a managed bot without BotFather, or connect Business / Hybrid manually."
        action={
          isConnected ? (
            <Badge tone="success">Connected</Badge>
          ) : account?.status === 'disabled' ? (
            <Badge tone="warning">Disabled</Badge>
          ) : (
            <Badge tone="neutral">Not connected</Badge>
          )
        }
      />
      <CardBody className="space-y-4">
        <p className="text-sm text-muted">
          Modira never asks for your Telegram password or OTP. Managed bots are created inside
          Telegram with one tap — no token is shown to you.
        </p>

        {account ? (
          <div className="grid gap-2 text-sm text-muted sm:grid-cols-2">
            <p>Mode: {modeLabel ?? 'Bot'}</p>
            <p className="flex items-center gap-2">
              Bot: {account.bot_username ? `@${account.bot_username}` : '—'}
              {account.managed_bot ? <Badge tone="neutral">Managed</Badge> : null}
            </p>
            <p>Webhook: {getWebhookStatusLabel(account)}</p>
            {showBusinessPanel ? (
              <>
                <p>
                  Real account:{' '}
                  {realAccountLabel ? (
                    <span className="text-fg">{realAccountLabel}</span>
                  ) : (
                    '—'
                  )}
                </p>
                <p className="flex items-center gap-2">
                  Business:
                  {businessActive ? (
                    <Badge tone="success">Connection active</Badge>
                  ) : (
                    <Badge tone="neutral">Not linked</Badge>
                  )}
                </p>
                <p>Last sync: {formatTelegramLastSync(account.telegram_last_sync_at)}</p>
                <p className="sm:col-span-2">
                  Rights: {formatTelegramRights(account.telegram_rights_json)}
                </p>
              </>
            ) : (
              <p>Validated: {formatValidationTime(account.last_validation_at)}</p>
            )}
          </div>
        ) : null}

        {account?.status === 'disabled' && account.last_error ? (
          <p className="rounded-lg border border-warning/30 bg-warning/5 p-3 text-sm text-warning">
            {account.last_error}
          </p>
        ) : null}

        {account?.last_error && account.status !== 'disabled' ? (
          <p className="text-sm text-danger">{account.last_error}</p>
        ) : null}

        {session ? (
          <div className="rounded-lg border border-border p-4 space-y-3">
            <p className="text-sm font-medium text-fg">
              Setup: {session.managed_bot ? 'Managed Bot' : MODE_LABELS[session.mode]} —{' '}
              {session.status.replace(/_/g, ' ')}
            </p>
            {session.status === 'waiting_managed_bot_approval' ? (
              <div className="space-y-3 text-sm text-muted">
                <p>
                  Open Telegram and approve bot creation. Suggested username:{' '}
                  <span className="text-fg">@{session.suggested_bot_username ?? '—'}</span>
                </p>
                {session.deep_link ? (
                  <a
                    href={session.deep_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex"
                  >
                    <Button type="button">Open in Telegram</Button>
                  </a>
                ) : null}
                <p>This page will update automatically once you approve.</p>
              </div>
            ) : null}
            {session.status === 'waiting_bot_token' && showAdvancedToken ? (
              <form onSubmit={handleSubmitToken} className="space-y-3">
                <Field label="Bot token">
                  <Input
                    type="password"
                    value={botToken}
                    onChange={(e) => setBotToken(e.target.value)}
                    required
                  />
                </Field>
                <Field label="Webhook secret (optional)">
                  <Input
                    type="password"
                    value={webhookSecret}
                    onChange={(e) => setWebhookSecret(e.target.value)}
                  />
                </Field>
                <Button type="submit" disabled={isConnecting || !canManage}>
                  Save bot token
                </Button>
              </form>
            ) : null}
            {session.status === 'waiting_business_connection' ? (
              <div className="space-y-2 text-sm text-muted">
                <p>
                  Open Telegram → Settings → Telegram Business → Chatbots → connect this bot to
                  your business account. This page will update automatically when linked.
                </p>
              </div>
            ) : null}
            {session.status === 'failed' && session.error_message ? (
              <p className="text-sm text-danger">{session.error_message}</p>
            ) : null}
            <Button
              variant="ghost"
              onClick={() => {
                void apiClient.cancelTelegramConnect(shopId, session.id);
                setSession(null);
              }}
            >
              Cancel setup
            </Button>
          </div>
        ) : null}

        {canManage ? (
          <div className="flex flex-wrap gap-2">
            {!isConnected ? (
              <>
                <Button onClick={() => void handleCreateManagedBot()} disabled={isConnecting}>
                  Create Bot
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => void handleStartConnect('business')}
                  disabled={isConnecting}
                >
                  Connect Business
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => void handleStartConnect('hybrid')}
                  disabled={isConnecting}
                >
                  Connect Hybrid
                </Button>
                {!session ? (
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setShowAdvancedToken((value) => !value);
                      if (!showAdvancedToken && !session) {
                        void handleStartConnect('bot');
                      }
                    }}
                    disabled={isConnecting}
                  >
                    {showAdvancedToken ? 'Hide advanced' : 'Advanced: paste bot token'}
                  </Button>
                ) : null}
              </>
            ) : (
              <>
                {showBusinessPanel ? (
                  <Button variant="secondary" onClick={() => void handleSync()} disabled={isSyncing}>
                    {isSyncing ? 'Syncing…' : 'Sync / Refresh'}
                  </Button>
                ) : null}
                {isManagedAccount ? (
                  <Button variant="secondary" onClick={() => void handleRotateToken()} disabled={isRotating}>
                    {isRotating ? 'Rotating…' : 'Rotate Token'}
                  </Button>
                ) : null}
                <Button variant="secondary" onClick={() => void handleReconnect()} disabled={isConnecting}>
                  Reconnect
                </Button>
                <Button variant="danger" onClick={() => void handleDisconnect()} disabled={isDisconnecting}>
                  Disconnect
                </Button>
                <Link
                  className="inline-flex items-center rounded-md px-3 py-2 text-sm text-muted hover:text-fg"
                  to={`/shops/${shopId}/inbox`}
                >
                  Human takeover (inbox)
                </Link>
              </>
            )}
          </div>
        ) : null}

        {showBusinessPanel && businessActive ? (
          <p className="text-xs text-muted">
            AI and operator replies in business mode are sent as your real Telegram account using the
            business connection.
          </p>
        ) : null}
      </CardBody>
    </Card>
  );
}
