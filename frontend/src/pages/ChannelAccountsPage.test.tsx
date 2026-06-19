import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import type { ChannelAccount, ChannelProvider } from '../types/channel';
import { ChannelAccountsPage } from './ChannelAccountsPage';

const mocks = vi.hoisted(() => ({
  listChannelAccounts: vi.fn(),
  createChannelAccount: vi.fn(),
  updateChannelCredentials: vi.fn(),
  updateChannelAccount: vi.fn(),
  validateChannelCredentials: vi.fn(),
  testChannelWebhook: vi.fn(),
  setTelegramWebhook: vi.fn(),
  getMe: vi.fn(),
  copyTextToClipboard: vi.fn(),
}));

vi.mock('../lib/channelAccounts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/channelAccounts')>();
  return {
    ...actual,
    copyTextToClipboard: mocks.copyTextToClipboard,
  };
});

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: mocks.getMe,
    listShops: vi.fn().mockResolvedValue([
      {
        id: 's1',
        name: 'Demo Shop',
        slug: 'demo',
        status: 'active',
        default_currency: 'USD',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]),
    listChannelAccounts: mocks.listChannelAccounts,
    createChannelAccount: mocks.createChannelAccount,
    updateChannelCredentials: mocks.updateChannelCredentials,
    updateChannelAccount: mocks.updateChannelAccount,
    validateChannelCredentials: mocks.validateChannelCredentials,
    testChannelWebhook: mocks.testChannelWebhook,
    setTelegramWebhook: mocks.setTelegramWebhook,
  },
}));

function makeAccount(provider: ChannelProvider, overrides: Partial<ChannelAccount> = {}): ChannelAccount {
  return {
    id: `ca-${provider}`,
    shop_id: 's1',
    provider,
    display_name: `${provider} main`,
    external_account_id: provider === 'instagram' || provider === 'whatsapp' ? `${provider}-ext` : null,
    phone_number_id: provider === 'whatsapp' ? 'phone-1' : null,
    bot_username: provider === 'telegram' ? 'shop_bot' : null,
    bot_id: null,
    status: 'connected',
    capabilities_json: { supports_text: true },
    settings_json: {},
    token_configured: provider === 'instagram' || provider === 'whatsapp',
    bot_token_configured: provider === 'telegram' || provider === 'bale' || provider === 'rubika',
    webhook_secret_configured: true,
    webhook_verify_token_configured: true,
    last_validation_at: null,
    last_error: null,
    created_at: '2026-06-12T00:00:00Z',
    updated_at: '2026-06-12T00:00:00Z',
    ...overrides,
  };
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ShopProvider>
          <ToastProvider>
            <ChannelAccountsPage />
          </ToastProvider>
        </ShopProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('ChannelAccountsPage', () => {
  beforeEach(() => {
    mocks.getMe.mockResolvedValue({
      id: 'u1',
      email: 'owner@example.com',
      full_name: 'Owner',
      role: 'owner',
    });
    mocks.listChannelAccounts.mockResolvedValue([]);
    mocks.copyTextToClipboard.mockResolvedValue(undefined);
    localStorage.setItem('dm_assistant_selected_shop_id', 's1');
  });

  afterEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  async function waitForShopReady() {
    expect(await screen.findByText('Add channel account')).toBeInTheDocument();
    await waitFor(() => {
      expect(mocks.listChannelAccounts).toHaveBeenCalledWith('s1');
    });
  }

  it('renders all supported providers in connected channels', async () => {
    const providers: ChannelProvider[] = ['instagram', 'whatsapp', 'telegram', 'bale', 'rubika'];
    mocks.listChannelAccounts.mockResolvedValue(providers.map((provider) => makeAccount(provider)));

    renderPage();
    await waitForShopReady();

    expect(await screen.findByRole('heading', { name: 'Channel Accounts' })).toBeInTheDocument();
    for (const provider of providers) {
      expect(await screen.findByText(`${provider} main`)).toBeInTheDocument();
    }
    expect(screen.getAllByText('Instagram').length).toBeGreaterThan(0);
    expect(screen.getAllByText('WhatsApp').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Telegram').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Bale').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Rubika').length).toBeGreaterThan(0);
  });

  it('does not display saved token values and shows configured status instead', async () => {
    const secretToken = 'super-secret-access-token-value';
    mocks.listChannelAccounts.mockResolvedValue([
      makeAccount('instagram', {
        token_configured: true,
      }),
    ]);

    renderPage();
    await waitForShopReady();
    await screen.findByText('instagram main');

    expect(screen.getAllByText('Configured').length).toBeGreaterThan(0);
    document.querySelectorAll('input[type="password"]').forEach((input) => {
      expect(input).not.toHaveValue(secretToken);
    });
    expect(screen.queryByDisplayValue(secretToken)).not.toBeInTheDocument();
  });

  it('renders configured and not configured credential badges', async () => {
    mocks.listChannelAccounts.mockResolvedValue([
      makeAccount('telegram', {
        bot_token_configured: true,
        webhook_secret_configured: false,
      }),
    ]);

    renderPage();

    await screen.findByText('telegram main');
    expect(screen.getByText('Configured')).toBeInTheDocument();
    expect(screen.getByText('Not configured')).toBeInTheDocument();
  });

  it('copies callback URL to clipboard', async () => {
    mocks.listChannelAccounts.mockResolvedValue([makeAccount('whatsapp')]);
    const user = userEvent.setup();
    renderPage();
    await waitForShopReady();

    await user.click(await screen.findByRole('button', { name: 'Copy callback URL' }));

    await waitFor(() => {
      expect(mocks.copyTextToClipboard).toHaveBeenCalledWith(
        expect.stringMatching(/\/api\/v1\/channels\/whatsapp\/webhook$/),
      );
    });
  });

  it('hides credential editing for operators', async () => {
    mocks.getMe.mockResolvedValue({
      id: 'u2',
      email: 'operator@example.com',
      full_name: 'Operator',
      role: 'operator',
    });
    mocks.listChannelAccounts.mockResolvedValue([makeAccount('telegram')]);

    renderPage();
    await waitForShopReady();

    await screen.findByText('telegram main');
    expect(screen.getByText('Credential changes restricted')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Replace token' })).not.toBeInTheDocument();
    expect(document.querySelector('input[type="password"]')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Validate credentials' })).not.toBeInTheDocument();
  });

  it('shows instagram required setup fields in create form', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitForShopReady();

    const providerSelect = screen.getByRole('combobox');
    await user.selectOptions(providerSelect, 'instagram');

    expect(screen.getByText('Instagram Business Account ID')).toBeInTheDocument();
    expect(screen.getByText('Facebook Page ID')).toBeInTheDocument();
    expect(screen.getByText('Webhook verify token')).toBeInTheDocument();
    expect(screen.getByText('Webhook secret')).toBeInTheDocument();
    expect(screen.getByText('Page access token')).toBeInTheDocument();
  });

  it('shows telegram bot token field in create form', async () => {
    const user = userEvent.setup();
    renderPage();
    await waitForShopReady();

    const providerSelect = screen.getByRole('combobox');
    await user.selectOptions(providerSelect, 'telegram');

    expect(screen.getByText('Bot token')).toBeInTheDocument();
  });

  it('calls validate credentials API from account card', async () => {
    mocks.listChannelAccounts.mockResolvedValue([makeAccount('telegram')]);
    mocks.validateChannelCredentials.mockResolvedValue(
      makeAccount('telegram', { last_validation_at: '2026-06-19T00:00:00Z' }),
    );
    const user = userEvent.setup();
    renderPage();
    await waitForShopReady();

    await user.click(await screen.findByRole('button', { name: 'Validate credentials' }));

    await waitFor(() => {
      expect(mocks.validateChannelCredentials).toHaveBeenCalledWith('s1', 'ca-telegram');
    });
  });

  it('renders security callout about encrypted write-only credentials', async () => {
    renderPage();
    expect(await screen.findByText('Credential security')).toBeInTheDocument();
    expect(screen.getByText(/Credentials are encrypted at rest/)).toBeInTheDocument();
    expect(screen.getByText(/never shown again after save/)).toBeInTheDocument();
  });

  it('opens replace credentials dialog for admins', async () => {
    mocks.listChannelAccounts.mockResolvedValue([makeAccount('instagram')]);
    const user = userEvent.setup();
    renderPage();
    await waitForShopReady();

    await user.click(await screen.findByRole('button', { name: 'Replace token' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('Replace credentials')).toBeInTheDocument();
    expect(within(dialog).getAllByPlaceholderText('Configured').length).toBeGreaterThan(0);
  });
});
