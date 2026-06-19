import { describe, expect, it } from 'vitest';

import {
  buildCallbackUrl,
  getPrimaryTokenConfigured,
  getSetupChecklist,
  getWebhookStatusLabel,
} from './channelAccounts';
import type { ChannelAccount } from '../types/channel';

function baseAccount(overrides: Partial<ChannelAccount> = {}): ChannelAccount {
  return {
    id: 'ca1',
    shop_id: 's1',
    provider: 'instagram',
    display_name: 'Test',
    status: 'draft',
    capabilities_json: {},
    settings_json: {},
    token_configured: false,
    bot_token_configured: false,
    webhook_secret_configured: false,
    webhook_verify_token_configured: false,
    created_at: '2026-06-12T00:00:00Z',
    updated_at: '2026-06-12T00:00:00Z',
    ...overrides,
  };
}

describe('channelAccounts helpers', () => {
  it('builds canonical callback URL per provider', () => {
    expect(buildCallbackUrl('whatsapp')).toMatch(/\/api\/v1\/channels\/whatsapp\/webhook$/);
    expect(buildCallbackUrl('telegram')).toMatch(/\/api\/v1\/channels\/telegram\/webhook$/);
  });

  it('derives primary token configured by provider', () => {
    expect(getPrimaryTokenConfigured(baseAccount({ provider: 'instagram', token_configured: true }))).toBe(true);
    expect(getPrimaryTokenConfigured(baseAccount({ provider: 'telegram', bot_token_configured: true }))).toBe(true);
  });

  it('derives webhook status label', () => {
    expect(getWebhookStatusLabel(baseAccount({ status: 'webhook_configured' }))).toBe('Configured');
    expect(
      getWebhookStatusLabel(
        baseAccount({ webhook_secret_configured: true, webhook_verify_token_configured: true }),
      ),
    ).toBe('Ready');
    expect(getWebhookStatusLabel(baseAccount())).toBe('Not configured');
  });

  it('builds instagram setup checklist', () => {
    const checklist = getSetupChecklist(
      baseAccount({
        provider: 'instagram',
        external_account_id: 'ig-1',
        settings_json: { page_id: 'page-1' },
        token_configured: true,
        webhook_secret_configured: true,
        webhook_verify_token_configured: true,
      }),
    );
    expect(checklist.find((item) => item.id === 'page_id')?.done).toBe(true);
    expect(checklist.find((item) => item.id === 'access_token')?.done).toBe(true);
  });
});
