import { FormEvent, useEffect, useState } from 'react';

import { Badge, Button, Dialog, Field, Input } from '../ui';
import { apiClient } from '../../services/apiClient';
import { configuredLabel } from '../../lib/channelAccounts';
import type { ChannelAccount } from '../../types/channel';
import { CredentialStatusRow } from './ChannelAccountCreateForm';

interface ChannelCredentialsDialogProps {
  open: boolean;
  account: ChannelAccount | null;
  shopId: string;
  canManage: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export function ChannelCredentialsDialog({
  open,
  account,
  shopId,
  canManage,
  onClose,
  onSaved,
}: ChannelCredentialsDialogProps) {
  const [externalAccountId, setExternalAccountId] = useState('');
  const [phoneNumberId, setPhoneNumberId] = useState('');
  const [botUsername, setBotUsername] = useState('');
  const [pageId, setPageId] = useState('');
  const [webhookVerifyToken, setWebhookVerifyToken] = useState('');
  const [webhookSecret, setWebhookSecret] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [botToken, setBotToken] = useState('');
  const [defaultLanguageCode, setDefaultLanguageCode] = useState('');
  const [templateNamespace, setTemplateNamespace] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !account) {
      return;
    }
    setExternalAccountId(account.external_account_id ?? '');
    setPhoneNumberId(account.phone_number_id ?? '');
    setBotUsername(account.bot_username ?? '');
    setPageId(String(account.settings_json?.page_id ?? ''));
    setDefaultLanguageCode(String(account.settings_json?.default_language_code ?? 'en_US'));
    setTemplateNamespace(String(account.settings_json?.message_template_namespace ?? ''));
    setWebhookVerifyToken('');
    setWebhookSecret('');
    setAccessToken('');
    setBotToken('');
    setError(null);
  }, [open, account]);

  if (!account || account.provider === 'instagram') {
    return null;
  }

  const isMetaProvider = account.provider === 'whatsapp';
  const isBotProvider = account.provider === 'telegram' || account.provider === 'bale' || account.provider === 'rubika';

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canManage || !account) {
      return;
    }
    const currentAccount = account;
    setIsSubmitting(true);
    setError(null);
    try {
      const settings: Record<string, unknown> = { ...currentAccount.settings_json };
      if (currentAccount.provider === 'instagram' && pageId) {
        settings.page_id = pageId;
      }
      if (currentAccount.provider === 'whatsapp') {
        if (defaultLanguageCode) {
          settings.default_language_code = defaultLanguageCode;
        }
        if (templateNamespace) {
          settings.message_template_namespace = templateNamespace;
        }
      }

      await apiClient.updateChannelAccount(shopId, currentAccount.id, {
        external_account_id: externalAccountId || undefined,
        phone_number_id: phoneNumberId || undefined,
        bot_username: botUsername || undefined,
        webhook_verify_token: webhookVerifyToken || undefined,
        settings,
      });

      const credentials: {
        webhook_secret?: string;
        access_token?: string;
        bot_token?: string;
        webhook_verify_token?: string;
      } = {};
      if (webhookSecret) {
        credentials.webhook_secret = webhookSecret;
      }
      if (accessToken) {
        credentials.access_token = accessToken;
      }
      if (botToken) {
        credentials.bot_token = botToken;
      }
      if (webhookVerifyToken) {
        credentials.webhook_verify_token = webhookVerifyToken;
      }

      if (Object.keys(credentials).length > 0) {
        await apiClient.updateChannelCredentials(shopId, currentAccount.id, credentials);
      }

      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update credentials');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Replace credentials"
      footer={
        canManage ? (
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" form="channel-credentials-form" disabled={isSubmitting}>
              Save credentials
            </Button>
          </div>
        ) : null
      }
    >
      <form id="channel-credentials-form" className="flex flex-col gap-4" onSubmit={handleSubmit}>
        <p className="text-sm text-muted">
          Tokens are write-only. Enter new values only when replacing credentials. Saved tokens are never shown again.
        </p>

        <div className="rounded-lg border border-border bg-surface-sunken p-3">
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Current status</p>
          <div className="flex flex-col gap-2">
            {isMetaProvider ? (
              <CredentialStatusRow label="Access token" configured={account.token_configured} />
            ) : (
              <CredentialStatusRow label="Bot token" configured={account.bot_token_configured} />
            )}
            <CredentialStatusRow
              label={account.provider === 'whatsapp' ? 'App secret' : 'Webhook secret'}
              configured={account.webhook_secret_configured}
            />
            <CredentialStatusRow
              label="Webhook verify token"
              configured={Boolean(account.webhook_verify_token_configured)}
            />
          </div>
        </div>

        {account.provider === 'whatsapp' && (
          <>
            <Field label="WABA ID">
              <Input
                value={externalAccountId}
                onChange={(event) => setExternalAccountId(event.target.value)}
                disabled={!canManage}
              />
            </Field>
            <Field label="Phone number ID">
              <Input
                value={phoneNumberId}
                onChange={(event) => setPhoneNumberId(event.target.value)}
                disabled={!canManage}
              />
            </Field>
            <Field label="Default language">
              <Input
                value={defaultLanguageCode}
                onChange={(event) => setDefaultLanguageCode(event.target.value)}
                disabled={!canManage}
              />
            </Field>
            <Field label="Template namespace">
              <Input
                value={templateNamespace}
                onChange={(event) => setTemplateNamespace(event.target.value)}
                disabled={!canManage}
              />
            </Field>
          </>
        )}

        {isBotProvider && (
          <Field label="Bot username">
            <Input value={botUsername} onChange={(event) => setBotUsername(event.target.value)} disabled={!canManage} />
          </Field>
        )}

        <Field label="Webhook verify token" hint="Leave blank to keep the current verify token.">
          <Input
            type="password"
            autoComplete="new-password"
            value={webhookVerifyToken}
            onChange={(event) => setWebhookVerifyToken(event.target.value)}
            disabled={!canManage}
            placeholder={account.webhook_verify_token_configured ? 'Configured' : 'Not configured'}
          />
        </Field>

        <Field
          label={account.provider === 'whatsapp' ? 'App secret' : 'Webhook secret'}
          hint={`Current: ${configuredLabel(account.webhook_secret_configured)}`}
        >
          <Input
            type="password"
            autoComplete="new-password"
            value={webhookSecret}
            onChange={(event) => setWebhookSecret(event.target.value)}
            disabled={!canManage}
            placeholder={account.webhook_secret_configured ? 'Configured' : 'Not configured'}
          />
        </Field>

        {isMetaProvider && (
          <Field
            label="Access token"
            hint={`Current: ${configuredLabel(account.token_configured)}`}
          >
            <Input
              type="password"
              autoComplete="new-password"
              value={accessToken}
              onChange={(event) => setAccessToken(event.target.value)}
              disabled={!canManage}
              placeholder={account.token_configured ? 'Configured' : 'Not configured'}
            />
          </Field>
        )}

        {isBotProvider && (
          <Field label="Bot token" hint={`Current: ${configuredLabel(account.bot_token_configured)}`}>
            <Input
              type="password"
              autoComplete="new-password"
              value={botToken}
              onChange={(event) => setBotToken(event.target.value)}
              disabled={!canManage}
              placeholder={account.bot_token_configured ? 'Configured' : 'Not configured'}
            />
          </Field>
        )}

        {!canManage ? (
          <Badge tone="warning">Only owner or admin can replace credentials.</Badge>
        ) : null}

        {error ? <p className="text-sm text-danger">{error}</p> : null}
      </form>
    </Dialog>
  );
}
