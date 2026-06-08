import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { DashboardPage } from './DashboardPage';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    getDashboardMetrics: vi.fn().mockResolvedValue({
      today_orders: 3,
      paid_orders: 2,
      waiting_for_payment: 1,
      handoff_conversations: 0,
      abandoned_orders: 4,
      recovered_orders: 1,
      recovered_revenue: '49.99',
      upsell_suggestions: 5,
      upsell_accepted: 1,
      top_selling_posts: [
        { instagram_post_url: 'https://instagram.com/p/top', paid_orders: 2, revenue: '99.98' },
      ],
      top_lost_demand_variants: [{ requested_color: 'Red', requested_size: 'XL', product_id: 'p1', count: 3 }],
      low_stock_variants: [],
      conversion_funnel: {
        inbound_messages: 10,
        product_resolved: 8,
        draft_orders: 5,
        paid_orders: 2,
      },
    }),
  },
}));

describe('DashboardPage', () => {
  it('renders revenue recovery widgets', async () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <AuthProvider>
          <ShopProvider>
            <MemoryRouter>
              <DashboardPage />
            </MemoryRouter>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    expect(await screen.findByText('Abandoned orders')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('Recovered revenue')).toBeInTheDocument();
    expect(screen.getByText('$49.99')).toBeInTheDocument();
    expect(screen.getByText('Conversion funnel')).toBeInTheDocument();
    expect(screen.getByText(/2 of 10 messages became a paid order/i)).toBeInTheDocument();
    expect(screen.getByText('Customers who DMed your shop')).toBeInTheDocument();
    expect(screen.getByText('20% of all messages')).toBeInTheDocument();
    expect(screen.getByText('https://instagram.com/p/top')).toBeInTheDocument();
  });
});
