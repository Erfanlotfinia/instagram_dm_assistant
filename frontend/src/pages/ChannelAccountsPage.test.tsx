import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
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
  startTelegramConnect: vi.fn(),
  getTelegramConnectSession: vi.fn(),
  submitTelegramBotToken: vi.fn(),
  completeTelegramConnect: vi.fn(),
  cancelTelegramConnect: vi.fn(),
  startInstagramConnect: vi.fn(),
  reconnectInstagram: vi.fn(),
  disconnectChannel: vi.fn(),
  getInstagramReadiness: vi.fn(),
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
    startTelegramConnect: mocks.startTelegramConnect,
    getTelegramConnectSession: mocks.getTelegramConnectSession,
    submitTelegramBotToken: mocks.submitTelegramBotToken,
    completeTelegramConnect: mocks.completeTelegramConnect,
    cancelTelegramConnect: mocks.cancelTelegramConnect,
    startInstagramConnect: mocks.startInstagramConnect,
    reconnectInstagram: mocks.reconnectInstagram,
    disconnectChannel: mocks.disconnectChannel,
    getInstagramReadiness: mocks.getInstagramReadiness,
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
            <MemoryRouter>
              <ChannelAccountsPage />
            </MemoryRouter>
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
    mocks.getInstagramReadiness.mockResolvedValue({
      meta_app_id_configured: true,
      meta_app_secret_configured: true,
      oauth_redirect_uri: 'http://localhost:8000/api/v1/channels/instagram/oauth/callback',
      data_deletion_callback_configured: false,
      privacy_policy_url: null,
      required_scopes: ['instagram_basic'],
      app_mode: 'development',
      webhook_callback_reachable: true,
      webhook_callback_url: 'http://localhost:8000/api/v1/channels/instagram/webhook',
      app_review_status: 'manual_check_required',
    });
    mocks.copyTextToClipboard.mockResolvedValue(undefined);
    localStorage.setItem('dm_assistant_selected_shop_id', 's1');
  });

  afterEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  async function waitForShopReady() {
    expect(await screen.findByText('Add other channel accounts')).toBeInTheDocument();
    await waitFor(() => {
      expect(mocks.listChannelAccounts).toHaveBeenCalledWith('s1');
    });
  }

  it('renders other supported providers in connected channels', async () => {
    const providers: ChannelProvider[] = ['whatsapp', 'bale', 'rubika'];
    mocks.listChannelAccounts.mockResolvedValue([
      ...providers.map((provider) => makeAccount(provider)),
      makeAccount('telegram', { bot_token_configured: true, status: 'connected' }),
    ]);

    renderPage();
    await waitForShopReady();

    expect(await screen.findByRole('heading', { name: 'Channel Accounts' })).toBeInTheDocument();
    for (const provider of providers) {
      expect(await screen.findByText(`${provider} main`)).toBeInTheDocument();
    }
    expect(screen.getByRole('button', { name: 'Connect Instagram' })).toBeInTheDocument();
    expect(screen.getAllByText('WhatsApp').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Telegram').length).toBeGreaterThan(0);
  });

  it('does not display saved token values for connected instagram card', async () => {
    mocks.listChannelAccounts.mockResolvedValue([
      makeAccount('instagram', {
        token_configured: true,
        settings_json: { instagram_username: 'demo_shop' },
      }),
    ]);

    renderPage();
    await waitForShopReady();

    expect(screen.getByText('Encrypted')).toBeInTheDocument();
    expect(screen.queryByDisplayValue('super-secret-access-token-value')).not.toBeInTheDocument();
  });

  it('renders configured and not configured credential badges', async () => {
    mocks.listChannelAccounts.mockResolvedValue([
      makeAccount('bale', {
        bot_token_configured: true,
        webhook_secret_configured: false,
      }),
    ]);

    renderPage();

    await screen.findByText('bale main');
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
    mocks.listChannelAccounts.mockResolvedValue([makeAccount('whatsapp')]);

    renderPage();
    await waitForShopReady();

    await screen.findByText('whatsapp main');
    expect(screen.getByText('Credential changes restricted')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Replace token' })).not.toBeInTheDocument();
    expect(document.querySelector('input[type="password"]')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Validate credentials' })).not.toBeInTheDocument();
  });

  it('does not show instagram manual fields in normal create form', async () => {
    renderPage();
    await waitForShopReady();

    const providerSelect = screen.getByRole('combobox');
    expect(providerSelect).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Instagram' })).not.toBeInTheDocument();
    expect(screen.queryByText('Page access token')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Connect Instagram' })).toBeInTheDocument();
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
    mocks.listChannelAccounts.mockResolvedValue([makeAccount('bale')]);
    mocks.validateChannelCredentials.mockResolvedValue(
      makeAccount('bale', { last_validation_at: '2026-06-19T00:00:00Z' }),
    );
    const user = userEvent.setup();
    renderPage();
    await waitForShopReady();

    await user.click(await screen.findByRole('button', { name: 'Validate credentials' }));

    await waitFor(() => {
      expect(mocks.validateChannelCredentials).toHaveBeenCalledWith('s1', 'ca-bale');
    });
  });

  it('renders security callout about encrypted write-only credentials', async () => {
    renderPage();
    expect(await screen.findByText('Credential security')).toBeInTheDocument();
    expect(screen.getByText(/Credentials are encrypted at rest/)).toBeInTheDocument();
    expect(screen.getByText(/never shown again after save/)).toBeInTheDocument();
  });

  it('keeps advanced instagram setup collapsed by default', async () => {
    renderPage();
    await waitForShopReady();
    expect(screen.getByText('Advanced / developer setup only')).toBeInTheDocument();
    expect(screen.queryByText('Save advanced setup')).not.toBeInTheDocument();
  });

  it('opens replace credentials dialog for bale admins', async () => {
    mocks.listChannelAccounts.mockResolvedValue([makeAccount('bale')]);
    const user = userEvent.setup();
    renderPage();
    await waitForShopReady();

    await user.click(await screen.findByRole('button', { name: 'Replace token' }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('Replace credentials')).toBeInTheDocument();
    expect(within(dialog).getAllByPlaceholderText('Configured').length).toBeGreaterThan(0);
  });
});
