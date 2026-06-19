import { useState } from 'react';

import { Badge, Button, Card, CardBody, CardHeader } from '../ui';
import { useToast } from '../../contexts/ToastContext';
import { apiClient } from '../../services/apiClient';
import {
  buildCallbackUrl,
  configuredLabel,
  copyTextToClipboard,
  formatValidationTime,
  getCapabilityLabels,
  getPrimaryTokenConfigured,
  getSetupChecklist,
  getStatusTone,
  getWebhookStatusLabel,
  providerLabel,
} from '../../lib/channelAccounts';
import type { ChannelAccount } from '../../types/channel';

interface ChannelAccountCardProps {
  account: ChannelAccount;
  shopId: string;
  canManage: boolean;
  onRefresh: () => void;
  onReplaceCredentials: (account: ChannelAccount) => void;
}

export function ChannelAccountCard({
  account,
  shopId,
  canManage,
  onRefresh,
  onReplaceCredentials,
}: ChannelAccountCardProps) {
  const { showToast } = useToast();
  const [isValidating, setIsValidating] = useState(false);
  const [isConfiguringWebhook, setIsConfiguringWebhook] = useState(false);
  const checklist = getSetupChecklist(account);
  const capabilities = getCapabilityLabels(account);

  async function copyCallbackUrl() {
    try {
      await copyTextToClipboard(buildCallbackUrl(account.provider));
      showToast('Callback URL copied to clipboard.', 'success');
    } catch {
      showToast('Could not copy callback URL.', 'error');
    }
  }

  async function handleValidate() {
    setIsValidating(true);
    try {
      await apiClient.validateChannelCredentials(shopId, account.id);
      showToast('Credential validation completed.', 'success');
      onRefresh();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Validation failed', 'error');
    } finally {
      setIsValidating(false);
    }
  }

  async function handleWebhookTest() {
    try {
      await apiClient.testChannelWebhook(shopId, account.id);
      showToast(`${providerLabel(account.provider)} webhook test accepted.`, 'success');
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Webhook test failed', 'error');
    }
  }

  async function handleConfigureWebhook() {
    setIsConfiguringWebhook(true);
    try {
      await apiClient.setTelegramWebhook(shopId, account.id);
      showToast('Telegram webhook configured.', 'success');
      onRefresh();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Configure webhook failed', 'error');
    } finally {
      setIsConfiguringWebhook(false);
    }
  }

  const primaryTokenLabel =
    account.provider === 'instagram' || account.provider === 'whatsapp' ? 'Access token' : 'Bot token';

  return (
    <Card>
      <CardHeader
        title={account.display_name}
        description={providerLabel(account.provider)}
        actions={
          <div className="flex flex-wrap gap-2">
            <Badge tone={getStatusTone(account.status)}>{account.status}</Badge>
            <Badge tone="neutral">Webhook: {getWebhookStatusLabel(account)}</Badge>
          </div>
        }
      />
      <CardBody className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-muted">Credentials</p>
            <div className="mt-2 flex flex-col gap-1 text-sm">
              <div className="flex justify-between gap-2">
                <span className="text-muted">{primaryTokenLabel}</span>
                <Badge tone={getPrimaryTokenConfigured(account) ? 'success' : 'neutral'}>
                  {configuredLabel(getPrimaryTokenConfigured(account))}
                </Badge>
              </div>
              <div className="flex justify-between gap-2">
                <span className="text-muted">
                  {account.provider === 'whatsapp' ? 'App secret' : 'Webhook secret'}
                </span>
                <Badge tone={account.webhook_secret_configured ? 'success' : 'neutral'}>
                  {configuredLabel(account.webhook_secret_configured)}
                </Badge>
              </div>
            </div>
          </div>

          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-muted">Validation</p>
            <dl className="mt-2 space-y-1 text-sm">
              <div className="flex justify-between gap-2">
                <dt className="text-muted">Last validation</dt>
                <dd className="text-fg">{formatValidationTime(account.last_validation_at)}</dd>
              </div>
              <div>
                <dt className="text-muted">Last error</dt>
                <dd className="mt-1 break-words text-fg">{account.last_error ?? '—'}</dd>
              </div>
            </dl>
          </div>

          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-muted">Capabilities</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {capabilities.length > 0 ? (
                capabilities.map((cap) => (
                  <Badge key={cap} tone="neutral">
                    {cap}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-muted">—</span>
              )}
            </div>
          </div>
        </div>

        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-muted">Setup checklist</p>
          <ul className="mt-2 space-y-1">
            {checklist.map((item) => (
              <li key={item.id} className="flex items-center gap-2 text-sm">
                <span aria-hidden="true">{item.done ? '✓' : '○'}</span>
                <span className={item.done ? 'text-fg' : 'text-muted'}>{item.label}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex flex-wrap gap-2 border-t border-border pt-4">
          <Button type="button" variant="secondary" size="sm" onClick={() => void copyCallbackUrl()}>
            Copy callback URL
          </Button>
          <Button type="button" variant="secondary" size="sm" onClick={() => void handleWebhookTest()}>
            Webhook test
          </Button>
          {canManage ? (
            <>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => void handleValidate()}
                disabled={isValidating}
              >
                Validate credentials
              </Button>
              <Button type="button" variant="secondary" size="sm" onClick={() => onReplaceCredentials(account)}>
                Replace token
              </Button>
              {account.provider === 'telegram' ? (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void handleConfigureWebhook()}
                  disabled={isConfiguringWebhook}
                >
                  Configure Telegram webhook
                </Button>
              ) : null}
            </>
          ) : null}
        </div>
      </CardBody>
    </Card>
  );
}
