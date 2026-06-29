import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { RevenueRecoveryPage } from './RevenueRecoveryPage';
import type { RevenueRecoveryDashboard } from '../types/sprint4Revenue';

vi.mock('../contexts/ShopContext', () => ({
  useShop: () => ({ selectedShopId: 's1', selectedShop: { id: 's1', name: 'Demo' } }),
}));

vi.mock('../lib/useRevenueRecovery', () => ({
  useRevenueRecovery: vi.fn(),
}));

vi.mock('../lib/useShopReadiness', () => ({
  useShopReadiness: vi.fn(),
}));

const dashboard: RevenueRecoveryDashboard = {
  opportunities: [
    {
      id: 'unpaid_order:o1',
      type: 'unpaid_order',
      severity: 'high',
      shop_id: 's1',
      order_id: 'o1',
      conversation_id: 'conv1',
      title: 'Unpaid order o1',
      reason: 'Order o1 is awaiting payment.',
      estimated_value: 500000,
      suggested_action: 'Resend the payment link and follow up.',
      action_to: '/orders/o1',
      source: 'order',
    },
  ],
  lostDemand: [],
  restockWaitlist: [],
  postInsights: [],
  totalEstimatedRecoverableValue: 500000,
  highPriorityCount: 1,
};

import { useRevenueRecovery } from '../lib/useRevenueRecovery';
import { useShopReadiness } from '../lib/useShopReadiness';

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <RevenueRecoveryPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('RevenueRecoveryPage', () => {
  it('renders the KPI row and priority opportunities', () => {
    vi.mocked(useRevenueRecovery).mockReturnValue({
      dashboard,
      isLoading: false,
      error: null,
      warnings: [],
      refetch: vi.fn(),
    });
    vi.mocked(useShopReadiness).mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
      channelStates: [{ provider: 'instagram', ready: true } as never],
      catalogScore: null,
      shopReadiness: { score: 90, readyForPilot: true, readyForAutomation: true, checks: [], blockingReasons: [], warnings: [] } as never,
    });

    renderPage();

    expect(screen.getByText('Revenue Recovery')).toBeInTheDocument();
    expect(screen.getByText('Recoverable value')).toBeInTheDocument();
    expect(screen.getByText('High-priority opportunities')).toBeInTheDocument();
    expect(screen.getByText('Unpaid order o1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create draft/i })).toBeInTheDocument();
  });

  it('renders an empty state when there are no opportunities', () => {
    vi.mocked(useRevenueRecovery).mockReturnValue({
      dashboard: { opportunities: [], lostDemand: [], restockWaitlist: [], postInsights: [], totalEstimatedRecoverableValue: null, highPriorityCount: 0 },
      isLoading: false,
      error: null,
      warnings: [],
      refetch: vi.fn(),
    });
    vi.mocked(useShopReadiness).mockReturnValue({
      data: null,
      isLoading: false,
      error: null,
      channelStates: [],
      catalogScore: null,
      shopReadiness: null,
    });

    renderPage();

    expect(screen.getByText(/No recovery opportunities yet/i)).toBeInTheDocument();
  });
});
