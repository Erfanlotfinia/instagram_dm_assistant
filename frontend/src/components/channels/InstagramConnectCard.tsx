import { useState } from 'react';

import { Badge, Button, Card, CardBody, CardHeader } from '../ui';
import { useToast } from '../../contexts/ToastContext';
import { apiClient } from '../../services/apiClient';
import {
  formatValidationTime,
  getWebhookStatusLabel,
} from '../../lib/channelAccounts';
import type { ChannelAccount } from '../../types/channel';

interface InstagramConnectCardProps {
  shopId: string;
  account: ChannelAccount | null;
  canManage: boolean;
  onRefresh: () => void;
}

export function InstagramConnectCard({
  shopId,
  account,
  canManage,
  onRefresh,
}: InstagramConnectCardProps) {
  const { showToast } = useToast();
  const [isConnecting, setIsConnecting] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);

  const isConnected =
    account !== null && account.status !== 'disabled' && account.token_configured;

  async function handleConnect() {
    setIsConnecting(true);
    try {
      const response = await apiClient.startInstagramConnect(shopId);
      window.location.assign(response.authorization_url);
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Could not start Instagram connect', 'error');
      setIsConnecting(false);
    }
  }

  async function handleReconnect() {
    if (!account) {
      return;
    }
    setIsConnecting(true);
    try {
      const response = await apiClient.reconnectInstagram(shopId, account.id);
      window.location.assign(response.authorization_url);
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Could not start reconnect', 'error');
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
      showToast('Instagram disconnected. Conversations and orders are preserved.', 'success');
      onRefresh();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Disconnect failed', 'error');
    } finally {
      setIsDisconnecting(false);
    }
  }

  const username = account?.settings_json?.instagram_username as string | undefined;
  const pageName = account?.settings_json?.page_name as string | undefined;
  const errorMessage = account?.last_error;

  return (
    <Card>
      <CardHeader
        title="Instagram"
        description="Connect your Instagram Business account through official Meta authorization."
        actions={
          isConnected ? (
            <Badge tone="success">Connected</Badge>
          ) : (
            <Badge tone="neutral">Not connected</Badge>
          )
        }
      />
      <CardBody className="flex flex-col gap-4">
        {!isConnected ? (
          <>
            <p className="text-sm text-muted">
              You&apos;ll be redirected to Meta to safely connect your Instagram Business account.
              Modira will never ask for your Instagram password.
            </p>
            {canManage ? (
              <Button type="button" onClick={() => void handleConnect()} disabled={isConnecting}>
                {isConnecting ? 'Redirecting…' : 'Connect Instagram'}
              </Button>
            ) : (
              <p className="text-sm text-muted">Contact an owner or admin to connect Instagram.</p>
            )}
          </>
        ) : (
          <>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-muted">Account</p>
                <p className="mt-1 text-sm text-fg">
                  {username ? `@${username}` : account?.display_name}
                  {pageName ? ` · ${pageName}` : null}
                </p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-muted">Access token</p>
                <Badge tone="success" className="mt-1">
                  Encrypted
                </Badge>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-muted">Webhook</p>
                <p className="mt-1 text-sm text-fg">{getWebhookStatusLabel(account!)}</p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-muted">Last validation</p>
                <p className="mt-1 text-sm text-fg">{formatValidationTime(account?.last_validation_at)}</p>
              </div>
            </div>
            {account?.last_error ? (
              <p className="text-sm text-danger">{errorMessage}</p>
            ) : null}
            {canManage ? (
              <div className="flex flex-wrap gap-2 border-t border-border pt-4">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void handleReconnect()}
                  disabled={isConnecting}
                >
                  Replace connection
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void handleDisconnect()}
                  disabled={isDisconnecting}
                >
                  Disconnect
                </Button>
              </div>
            ) : null}
            <p className="text-xs text-muted">
              Disconnect disables messaging but does not delete conversations or orders.
            </p>
          </>
        )}
      </CardBody>
    </Card>
  );
}
