import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { PostRevenueAnalyticsPage } from './PostRevenueAnalyticsPage';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    getPostRevenueAnalytics: vi.fn().mockResolvedValue([
      {
        instagram_post_url: 'https://instagram.com/p/abc',
        product_id: 'p1',
        conversations: 10,
        draft_orders: 4,
        paid_orders: 2,
        revenue: '120.00',
        conversion_rate: 0.2,
        abandoned_rate: 0.5,
      },
    ]),
  },
}));

describe('PostRevenueAnalyticsPage', () => {
  it('renders post revenue table', async () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <AuthProvider>
          <ShopProvider>
            <MemoryRouter>
              <PostRevenueAnalyticsPage />
            </MemoryRouter>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    expect((await screen.findAllByText('https://instagram.com/p/abc')).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('120.00')).toBeInTheDocument();
    expect(screen.getAllByText('20.0%').length).toBeGreaterThanOrEqual(1);
  });
});
