import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { AnalyticsPage } from './AnalyticsPage';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    getAnalyticsFunnel: vi.fn().mockResolvedValue({
      inbound_messages: 12,
      resolved_product_rate: 0.75,
      product_resolved_rate: 0.75,
      variant_resolved_rate: 0.5,
      payment_conversion_rate: 0.2,
      paid_orders: 2,
      revenue: '199.98',
    }),
    getAnalyticsPosts: vi.fn().mockResolvedValue([]),
    getAnalyticsStockDemand: vi.fn().mockResolvedValue([]),
    getAnalyticsUnavailableDemand: vi.fn().mockResolvedValue([]),
    getAnalyticsHandoff: vi.fn().mockResolvedValue([]),
    getPostRevenueAnalytics: vi.fn().mockResolvedValue([]),
    getAnalyticsLostDemand: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25 }),
    getAnalyticsAgentPerformance: vi.fn().mockResolvedValue({
      auto_sent_messages: 3,
      preview_required_messages: 1,
      handoff_rate: 0.1,
      failed_agent_runs: 0,
      invalid_llm_outputs: 0,
      average_intent_confidence: 0.91,
      average_product_confidence: 0.88,
      average_variant_confidence: 0.86,
    }),
    getAnalyticsOperatorPerformance: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 25 }),
  },
}));

describe('AnalyticsPage', () => {
  it('renders funnel cards and agent performance', async () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <AuthProvider>
          <ShopProvider>
            <MemoryRouter>
              <AnalyticsPage />
            </MemoryRouter>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    expect(await screen.findByRole('heading', { name: 'Funnel cards' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Agent performance' })).toBeInTheDocument();
    expect(screen.getByText('Auto-sent messages')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });
});
