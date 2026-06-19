import { FormEvent, useState } from 'react';

import { Badge, Button, Field, Input, Select } from '../ui';
import { useToast } from '../../contexts/ToastContext';
import {
  buildCallbackUrl,
  configuredLabel,
  copyTextToClipboard,
  PROVIDER_META,
  providerLabel,
} from '../../lib/channelAccounts';
import type { ChannelProvider } from '../../types/channel';

interface ChannelAccountCreateFormProps {
  disabled?: boolean;
  onSubmit: (payload: {
    provider: ChannelProvider;
    displayName: string;
    externalAccountId: string;
    phoneNumberId: string;
    botUsername: string;
    botId: string;
    pageId: string;
    webhookVerifyToken: string;
    webhookSecret: string;
    accessToken: string;
    botToken: string;
    defaultLanguageCode: string;
    templateNamespace: string;
  }) => Promise<void>;
}

export function ChannelAccountCreateForm({ disabled = false, onSubmit }: ChannelAccountCreateFormProps) {
  const { showToast } = useToast();
  const [provider, setProvider] = useState<ChannelProvider | ''>('');
  const [displayName, setDisplayName] = useState('');
  const [externalAccountId, setExternalAccountId] = useState('');
  const [phoneNumberId, setPhoneNumberId] = useState('');
  const [botUsername, setBotUsername] = useState('');
  const [botId, setBotId] = useState('');
  const [pageId, setPageId] = useState('');
  const [webhookVerifyToken, setWebhookVerifyToken] = useState('');
  const [webhookSecret, setWebhookSecret] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [botToken, setBotToken] = useState('');
  const [defaultLanguageCode, setDefaultLanguageCode] = useState('en_US');
  const [templateNamespace, setTemplateNamespace] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selectedProvider = PROVIDER_META.find((item) => item.value === provider);
  const isBotProvider = provider === 'telegram' || provider === 'bale' || provider === 'rubika';
  const isMetaProvider = provider === 'whatsapp';

  async function copyCallbackUrl() {
    if (!provider) {
      return;
    }
    try {
      await copyTextToClipboard(buildCallbackUrl(provider));
      showToast('Callback URL copied to clipboard.', 'success');
    } catch {
      showToast('Could not copy callback URL.', 'error');
    }
  }

  function resetForm() {
    setDisplayName('');
    setExternalAccountId('');
    setPhoneNumberId('');
    setBotUsername('');
    setBotId('');
    setPageId('');
    setWebhookVerifyToken('');
    setWebhookSecret('');
    setAccessToken('');
    setBotToken('');
    setDefaultLanguageCode('en_US');
    setTemplateNamespace('');
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!provider || disabled) {
      return;
    }
    setIsSubmitting(true);
    try {
      await onSubmit({
        provider,
        displayName,
        externalAccountId,
        phoneNumberId,
        botUsername,
        botId,
        pageId,
        webhookVerifyToken,
        webhookSecret,
        accessToken,
        botToken,
        defaultLanguageCode,
        templateNamespace,
      });
      resetForm();
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleSubmit}>
      <Field label="Provider" hint={selectedProvider?.hint}>
        <Select
          value={provider}
          onChange={(event) => setProvider(event.target.value as ChannelProvider | '')}
          required
          disabled={disabled}
        >
          <option value="">Select a channel</option>
          {PROVIDER_META.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Display name">
        <Input
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          required
          disabled={disabled || !provider}
        />
      </Field>

      {provider === 'whatsapp' && (
        <>
          <Field label="WABA ID">
            <Input
              value={externalAccountId}
              onChange={(event) => setExternalAccountId(event.target.value)}
              required
              disabled={disabled}
            />
          </Field>
          <Field label="Phone number ID">
            <Input
              value={phoneNumberId}
              onChange={(event) => setPhoneNumberId(event.target.value)}
              required
              disabled={disabled}
            />
          </Field>
          <Field label="Default language" hint="Optional template language code.">
            <Input
              value={defaultLanguageCode}
              onChange={(event) => setDefaultLanguageCode(event.target.value)}
              placeholder="en_US"
              disabled={disabled}
            />
          </Field>
          <Field label="Template namespace" hint="Optional WhatsApp template namespace.">
            <Input
              value={templateNamespace}
              onChange={(event) => setTemplateNamespace(event.target.value)}
              disabled={disabled}
            />
          </Field>
        </>
      )}

      {isBotProvider && (
        <>
          <Field label="Bot username">
            <Input value={botUsername} onChange={(event) => setBotUsername(event.target.value)} disabled={disabled} />
          </Field>
          <Field label="Bot ID">
            <Input value={botId} onChange={(event) => setBotId(event.target.value)} disabled={disabled} />
          </Field>
        </>
      )}

      {provider && (
        <>
          <Field label="Webhook verify token">
            <Input
              value={webhookVerifyToken}
              onChange={(event) => setWebhookVerifyToken(event.target.value)}
              disabled={disabled}
            />
          </Field>
          <Field label={provider === 'whatsapp' ? 'App secret' : 'Webhook secret'}>
            <Input
              type="password"
              autoComplete="new-password"
              value={webhookSecret}
              onChange={(event) => setWebhookSecret(event.target.value)}
              disabled={disabled}
            />
          </Field>
        </>
      )}

      {isMetaProvider && provider && (
        <Field label="Access token">
          <Input
            type="password"
            autoComplete="new-password"
            value={accessToken}
            onChange={(event) => setAccessToken(event.target.value)}
            disabled={disabled}
          />
        </Field>
      )}

      {isBotProvider && (
        <Field label="Bot token">
          <Input
            type="password"
            autoComplete="new-password"
            value={botToken}
            onChange={(event) => setBotToken(event.target.value)}
            disabled={disabled}
          />
        </Field>
      )}

      {provider ? (
        <div className="sm:col-span-2 rounded-lg border border-info/30 bg-info-soft/30 px-4 py-3 text-sm text-fg">
          <p>
            Configure the webhook callback URL in your {providerLabel(provider)} provider console:
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <code className="break-all text-xs">{buildCallbackUrl(provider)}</code>
            <Button type="button" variant="secondary" size="sm" onClick={() => void copyCallbackUrl()}>
              Copy callback URL
            </Button>
          </div>
          {provider === 'telegram' ? (
            <p className="mt-2 text-muted">
              After saving credentials, use Configure Telegram webhook to register the runtime URL with Telegram.
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="flex items-end sm:col-span-2">
        <Button type="submit" disabled={disabled || !provider || isSubmitting}>
          Add channel
        </Button>
      </div>
    </form>
  );
}

export function CredentialStatusRow({ label, configured }: { label: string; configured: boolean }) {
  return (
    <div className="flex items-center justify-between gap-2 text-sm">
      <span className="text-muted">{label}</span>
      <Badge tone={configured ? 'success' : 'neutral'}>{configuredLabel(configured)}</Badge>
    </div>
  );
}
