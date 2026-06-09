import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import { OrderDetailPage } from './OrderDetailPage';

const mocks = vi.hoisted(() => ({
  markPaid: vi.fn().mockResolvedValue({
    id: 'o1',
    status: 'paid',
    payment_status: 'paid',
  }),
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    getOrder: vi.fn().mockResolvedValue({
      id: 'o1',
      shop_id: 's1',
      status: 'waiting_for_payment',
      payment_status: 'pending',
      shipping_status: 'not_started',
      total_amount: '49.99',
      currency: 'USD',
      customer_name: 'Ali Rezaei',
      timeline: [],
      items: [],
      payments: [],
      shipments: [],
    }),
    markOrderPaid: mocks.markPaid,
  },
}));

vi.mock('../components/ConfirmDialog', () => ({
  ConfirmDialog: ({
    open,
    onConfirm,
  }: {
    open: boolean;
    onConfirm: () => void;
  }) => (open ? <button type="button" onClick={onConfirm}>Confirm paid</button> : null),
}));

describe('OrderDetailPage', () => {
  it('marks order as paid after confirmation', async () => {
    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ShopProvider>
            <ToastProvider>
              <MemoryRouter initialEntries={['/orders/o1?shopId=s1']}>
                <Routes>
                  <Route path="/orders/:orderId" element={<OrderDetailPage />} />
                </Routes>
              </MemoryRouter>
            </ToastProvider>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    const markPaidButton = await screen.findByRole('button', { name: /mark paid/i });
    await user.click(markPaidButton);
    const confirmButton = await screen.findByRole('button', { name: /confirm paid/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mocks.markPaid).toHaveBeenCalledWith('s1', 'o1');
    });
  });
});
