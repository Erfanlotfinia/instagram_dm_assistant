import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { OrdersPage } from './OrdersPage';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    listOrders: vi.fn().mockResolvedValue([
      {
        id: 'o1',
        shop_id: 's1',
        status: 'waiting_for_payment',
        payment_status: 'pending',
        shipping_status: 'not_started',
        total_amount: '49.99',
        currency: 'USD',
        customer_name: 'Ali Rezaei',
        created_at: '2026-06-07T10:00:00Z',
        updated_at: '2026-06-07T10:00:00Z',
      },
    ]),
  },
}));

describe('OrdersPage', () => {
  it('renders orders for selected shop', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ShopProvider>
            <MemoryRouter>
              <OrdersPage />
            </MemoryRouter>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Ali Rezaei|waiting_for_payment|49.99/i)).toBeInTheDocument();
    });
  });
});
