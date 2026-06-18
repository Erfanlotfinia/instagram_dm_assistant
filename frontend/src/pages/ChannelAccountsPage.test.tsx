import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ChannelAccountsPage } from './ChannelAccountsPage';

const mocks = vi.hoisted(() => ({
  listChannelAccounts: vi.fn(),
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'owner@example.com', full_name: 'Owner', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo Shop', slug: 'demo', status: 'active', default_currency: 'USD', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }]),
    listChannelAccounts: mocks.listChannelAccounts,
    createChannelAccount: vi.fn(),
    testChannelWebhook: vi.fn(),
  },
}));

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ShopProvider>
          <ChannelAccountsPage />
        </ShopProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('ChannelAccountsPage', () => {
  it('renders provider setup form and connected channel rows', async () => {
    mocks.listChannelAccounts.mockResolvedValue([
      {
        id: 'ca1',
        shop_id: 's1',
        provider: 'whatsapp',
        display_name: 'WhatsApp main',
        external_account_id: 'waba-1',
        phone_number_id: 'phone-1',
        bot_username: null,
        bot_id: null,
        status: 'connected',
        capabilities_json: { supports_templates: true, supports_customer_service_window: true },
        settings_json: {},
        created_at: '2026-06-12T00:00:00Z',
        updated_at: '2026-06-12T00:00:00Z',
      },
    ]);

    renderPage();

    expect(await screen.findByRole('heading', { name: 'Channel Accounts' })).toBeInTheDocument();
    expect(await screen.findByRole('combobox')).toBeInTheDocument();
    expect(await screen.findByText('WhatsApp main')).toBeInTheDocument();
    expect(screen.getByText('Webhook test')).toBeInTheDocument();
  });
});
