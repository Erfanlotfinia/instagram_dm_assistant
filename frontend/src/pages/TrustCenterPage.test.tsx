import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import { TrustCenterPage } from './TrustCenterPage';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    refresh: vi.fn().mockResolvedValue({ user: { id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' } }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    listScenarioPacks: vi.fn().mockResolvedValue([]),
    listReplayRuns: vi.fn().mockResolvedValue([]),
    createScenarioPack: vi.fn().mockResolvedValue({
      id: 'pack-1',
      shop_id: 's1',
      name: '[Trust] Prompt Injection Basics',
      pack_type: 'handcrafted',
      scenarios_json: [],
      is_golden: false,
    }),
    runReplay: vi.fn().mockResolvedValue({ run: { id: 'run-1' } }),
    getReplayRun: vi.fn().mockResolvedValue({ id: 'run-1', items: [] }),
  },
}));

vi.mock('../lib/useShopReadiness', () => ({
  useShopReadiness: () => ({
    data: null,
    isLoading: false,
    error: null,
    channelStates: [],
    catalogScore: null,
    shopReadiness: null,
  }),
}));

describe('TrustCenterPage', () => {
  it('renders header, KPI labels, and the four built-in pack cards', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ShopProvider>
            <ToastProvider>
              <MemoryRouter>
                <TrustCenterPage />
              </MemoryRouter>
            </ToastProvider>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText('Trust Center')).toBeInTheDocument();
    });

    expect(screen.getByText('Test packs')).toBeInTheDocument();
    expect(await screen.findByText('Prompt Injection Basics')).toBeInTheDocument();
    expect(screen.getByText('Commerce Safety')).toBeInTheDocument();
    expect(screen.getByText('Privacy & Secret Protection')).toBeInTheDocument();
    expect(screen.getByText('Policy Boundary')).toBeInTheDocument();
  });

  it('shows the connect-to-regression empty state before any run', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ShopProvider>
            <ToastProvider>
              <MemoryRouter>
                <TrustCenterPage />
              </MemoryRouter>
            </ToastProvider>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(
        screen.getAllByText('Connect this pack to Scenario Regression to run live simulations.').length,
      ).toBeGreaterThan(0);
    });
    expect(screen.getByText('No evaluation run yet')).toBeInTheDocument();
  });
});
