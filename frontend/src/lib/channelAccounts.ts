import type { ChannelAccount, ChannelProvider } from '../types/channel';

export interface ProviderMeta {
  value: ChannelProvider;
  label: string;
  hint: string;
}

export const PROVIDER_META: ProviderMeta[] = [
  { value: 'bale', label: 'Bale', hint: 'Telegram-like bot endpoint with Bale token and webhook limits.' },
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

export function buildCallbackUrl(provider: ChannelProvider, accountId?: string): string {
  if (provider === 'instagram' && accountId) {
    return `${getPublicApiBaseUrl()}/api/v1/channels/instagram/${accountId}/webhook`;
  }
  return `${getPublicApiBaseUrl()}/api/v1/channels/${provider}/webhook`;
}

export const INSTAGRAM_CONNECT_ERROR_MESSAGES: Record<string, string> = {
  no_business_account: 'No Instagram Business account found.',
  no_page_connected: 'Please connect your Instagram account to a Facebook Page.',
  missing_permissions: 'Missing required permissions. Reconnect and grant all requested permissions.',
  app_not_approved: 'Meta app review may be required before Instagram messaging works in live mode.',
  token_exchange_failed: 'Could not complete Meta authorization. Try connecting again.',
  webhook_setup_failed: 'Instagram connected but webhook setup could not be confirmed.',
  validation_failed: 'Connected account could not be validated with Meta.',
  connection_expired: 'Connection expired. Try again.',
};

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
          id: 'connection_mode',
          label: 'Connection mode',
          done: Boolean(account.connection_mode),
        },
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
      if (account.provider === 'telegram' && account.connection_mode !== 'bot') {
        items.push({
          id: 'business_connection',
          label: 'Business connection',
          done: Boolean(account.telegram_business_enabled && account.telegram_business_connection_id),
        });
      }
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
    case 'disconnected':
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

const TELEGRAM_RIGHT_LABELS: Record<string, string> = {
  can_reply: 'Reply to messages',
  can_read_messages: 'Read messages',
  can_delete_sent_messages: 'Delete sent messages',
  can_delete_all_messages: 'Delete all messages',
  can_edit_name: 'Edit name',
  can_edit_bio: 'Edit bio',
  can_edit_profile_photo: 'Edit profile photo',
  can_edit_username: 'Edit username',
  can_view_gifts_and_stars: 'View gifts and stars',
};

export function formatTelegramRights(rights: Record<string, unknown> | undefined | null): string {
  if (!rights || Object.keys(rights).length === 0) {
    return 'No rights reported';
  }
  const enabled = Object.entries(rights)
    .filter(([, value]) => value === true)
    .map(([key]) => TELEGRAM_RIGHT_LABELS[key] ?? key.replace(/_/g, ' '));
  return enabled.length > 0 ? enabled.join(', ') : 'No active rights';
}

export function formatTelegramLastSync(iso: string | null | undefined): string {
  if (!iso) {
    return 'Never synced';
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString();
}

export function getTelegramAccountLabel(account: ChannelAccount): string | null {
  if (account.telegram_username) {
    return `@${account.telegram_username}`;
  }
  if (account.telegram_user_id) {
    return `User ${account.telegram_user_id}`;
  }
  return null;
}

export function isTelegramBusinessActive(account: ChannelAccount): boolean {
  return Boolean(account.telegram_business_enabled && account.telegram_business_connection_id);
}
