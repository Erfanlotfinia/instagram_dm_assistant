import type { ChannelAccount, ChannelProvider } from '../types/channel';

export interface ProviderMeta {
  value: ChannelProvider;
  label: string;
  hint: string;
}

export const PROVIDER_META: ProviderMeta[] = [
  { value: 'bale', label: 'Bale', hint: 'Telegram-like bot endpoint with Bale token and webhook limits.' },
  { value: 'instagram', label: 'Instagram', hint: 'Meta webhook signature and Instagram Graph send APIs.' },
  { value: 'rubika', label: 'Rubika', hint: 'HTTPS endpoint mode, receiveUpdate and receiveInlineMessage support.' },
  { value: 'telegram', label: 'Telegram', hint: 'Bot API token with optional X-Telegram-Bot-Api-Secret-Token webhook header.' },
  { value: 'whatsapp', label: 'WhatsApp', hint: 'Cloud API phone number ID, verify token, templates and 24h service window.' },
];

export function providerLabel(provider: ChannelProvider): string {
  return PROVIDER_META.find((item) => item.value === provider)?.label ?? provider;
}

const DEFAULT_API_BASE_URL =
  typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.hostname}:8000` : 'http://localhost:8000';

export function getPublicApiBaseUrl(): string {
  const configured =
    import.meta.env.VITE_PUBLIC_API_BASE_URL ||
    import.meta.env.VITE_API_BASE_URL ||
    (typeof window !== 'undefined' ? window.location.origin : DEFAULT_API_BASE_URL);
  return configured.replace(/\/$/, '');
}

export function buildCallbackUrl(provider: ChannelProvider): string {
  return `${getPublicApiBaseUrl()}/api/v1/channels/${provider}/webhook`;
}

export async function copyTextToClipboard(text: string): Promise<void> {
  await navigator.clipboard.writeText(text);
}

export function getPrimaryTokenConfigured(account: ChannelAccount): boolean {
  if (account.provider === 'instagram' || account.provider === 'whatsapp') {
    return account.token_configured;
  }
  return account.bot_token_configured;
}

export function getWebhookStatusLabel(account: ChannelAccount): string {
  if (account.status === 'webhook_configured') {
    return 'Configured';
  }
  if (account.webhook_secret_configured && account.webhook_verify_token_configured) {
    return 'Ready';
  }
  if (account.webhook_secret_configured || account.webhook_verify_token_configured) {
    return 'Partial';
  }
  return 'Not configured';
}

export interface SetupChecklistItem {
  id: string;
  label: string;
  done: boolean;
}

export function getSetupChecklist(account: ChannelAccount): SetupChecklistItem[] {
  const items: SetupChecklistItem[] = [
    {
      id: 'display_name',
      label: 'Display name set',
      done: Boolean(account.display_name?.trim()),
    },
  ];

  switch (account.provider) {
    case 'instagram':
      items.push(
        {
          id: 'external_account_id',
          label: 'Instagram Business Account ID',
          done: Boolean(account.external_account_id),
        },
        {
          id: 'page_id',
          label: 'Facebook Page ID',
          done: Boolean(account.settings_json?.page_id),
        },
        {
          id: 'access_token',
          label: 'Page access token',
          done: account.token_configured,
        },
        {
          id: 'webhook_verify_token',
          label: 'Webhook verify token',
          done: Boolean(account.webhook_verify_token_configured),
        },
        {
          id: 'webhook_secret',
          label: 'Webhook secret',
          done: account.webhook_secret_configured,
        },
      );
      break;
    case 'whatsapp':
      items.push(
        {
          id: 'external_account_id',
          label: 'WABA ID',
          done: Boolean(account.external_account_id),
        },
        {
          id: 'phone_number_id',
          label: 'Phone number ID',
          done: Boolean(account.phone_number_id),
        },
        {
          id: 'access_token',
          label: 'Access token',
          done: account.token_configured,
        },
        {
          id: 'webhook_verify_token',
          label: 'Webhook verify token',
          done: Boolean(account.webhook_verify_token_configured),
        },
        {
          id: 'webhook_secret',
          label: 'App secret',
          done: account.webhook_secret_configured,
        },
      );
      break;
    case 'telegram':
    case 'bale':
    case 'rubika':
      items.push(
        {
          id: 'bot_username',
          label: 'Bot username',
          done: Boolean(account.bot_username),
        },
        {
          id: 'bot_token',
          label: 'Bot token',
          done: account.bot_token_configured,
        },
        {
          id: 'webhook_secret',
          label: 'Webhook secret',
          done: account.webhook_secret_configured,
        },
      );
      if (account.provider === 'telegram') {
        items.push({
          id: 'webhook_verify_token',
          label: 'Webhook verify token',
          done: Boolean(account.webhook_verify_token_configured),
        });
      }
      break;
    default:
      break;
  }

  return items;
}

export function formatValidationTime(iso: string | null | undefined): string {
  if (!iso) {
    return 'Never';
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString();
}

export function getStatusTone(status: ChannelAccount['status']): 'success' | 'warning' | 'danger' | 'neutral' {
  switch (status) {
    case 'connected':
    case 'webhook_configured':
      return 'success';
    case 'error':
      return 'danger';
    case 'disabled':
      return 'warning';
    default:
      return 'neutral';
  }
}

export function getCapabilityLabels(account: ChannelAccount): string[] {
  return Object.entries(account.capabilities_json)
    .filter(([, enabled]) => enabled === true)
    .map(([key]) => key.replace(/^supports_/, '').replace(/_/g, ' '));
}

export function configuredLabel(configured: boolean): string {
  return configured ? 'Configured' : 'Not configured';
}
