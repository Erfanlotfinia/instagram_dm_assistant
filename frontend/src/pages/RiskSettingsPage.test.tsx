import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider, useShop } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import { RiskSettingsPage } from './RiskSettingsPage';

vi.mock('../contexts/ShopContext', async () => {
  const actual = await vi.importActual<typeof import('../contexts/ShopContext')>('../contexts/ShopContext');
  return {
    ...actual,
    useShop: vi.fn(),
  };
});

const mocks = vi.hoisted(() => {
  const mockSettings = {
    shop_id: 's1',
    intent_confidence_threshold: 0.75,
    slot_confidence_threshold: 0.85,
    product_confidence_threshold: 0.8,
    variant_confidence_threshold: 0.85,
    address_confidence_threshold: 0.8,
    high_value_order_threshold: 500000,
    handoff_for_high_risk: true,
    handoff_for_low_variant_confidence: false,
    preview_required_for_high_value_order: true,
  };
  return {
    mockSettings,
    getAgentRiskSettings: vi.fn().mockResolvedValue(mockSettings),
    updateAgentRiskSettings: vi.fn(),
  };
});

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    getAgentRiskSettings: mocks.getAgentRiskSettings,
    updateAgentRiskSettings: mocks.updateAgentRiskSettings.mockResolvedValue({
      ...mocks.mockSettings,
      intent_confidence_threshold: 0.8,
    }),
  },
}));

function mockSelectedShop() {
  vi.mocked(useShop).mockReturnValue({
    shops: [{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }],
    selectedShopId: 's1',
    selectedShop: { id: 's1', name: 'Demo', slug: 'demo', status: 'active' },
    setSelectedShopId: vi.fn(),
    isLoading: false,
    error: null,
  });
}

function renderPage() {
  mockSelectedShop();
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AuthProvider>
        <ShopProvider>
          <ToastProvider>
            <MemoryRouter>
              <RiskSettingsPage />
            </MemoryRouter>
          </ToastProvider>
        </ShopProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('RiskSettingsPage', () => {
  it('asks for a selected shop before rendering the form', async () => {
    vi.mocked(useShop).mockReturnValue({
      shops: [],
      selectedShopId: '',
      selectedShop: null,
      setSelectedShopId: vi.fn(),
      isLoading: false,
      error: null,
    });

    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <ToastProvider>
          <MemoryRouter>
            <RiskSettingsPage />
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>,
    );

    expect(await screen.findByText(/Select a shop/i)).toBeInTheDocument();
  });

  it('renders grouped settings and policy snapshot', async () => {
    renderPage();

    expect(await screen.findByRole('heading', { name: /risk settings/i })).toBeInTheDocument();
    expect(await screen.findByText(/Current policy snapshot/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Confidence thresholds/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Handoff & preview policy/i })).toBeInTheDocument();
    expect(await screen.findByLabelText(/Intent confidence/i)).toHaveValue(0.75);
    expect(screen.getByText(/Handoff on high risk/i)).toBeInTheDocument();
  });

  it('saves updated settings without shop_id in payload', async () => {
    const user = userEvent.setup();
    renderPage();

    const intentInput = await screen.findByLabelText(/Intent confidence/i);
    await user.clear(intentInput);
    await user.type(intentInput, '0.8');

    const saveButton = screen.getByRole('button', { name: /save risk settings/i });
    await waitFor(() => expect(saveButton).not.toBeDisabled());
    await user.click(saveButton);

    await waitFor(() =>
      expect(mocks.updateAgentRiskSettings).toHaveBeenCalledWith('s1', expect.objectContaining({
        intent_confidence_threshold: 0.8,
      })),
    );

    expect(mocks.updateAgentRiskSettings.mock.calls[0][1]).not.toHaveProperty('shop_id');
  });

  it('shows load errors', async () => {
    mocks.getAgentRiskSettings.mockRejectedValueOnce(new Error('boom'));
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
  });
});
