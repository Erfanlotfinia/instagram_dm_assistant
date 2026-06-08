import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import { UpsellRulesPage } from './UpsellRulesPage';

const mocks = vi.hoisted(() => ({
  createProductUpsell: vi.fn().mockResolvedValue({ id: 'u1' }),
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    listProducts: vi.fn().mockResolvedValue([
      { id: 'p1', title: 'Hoodie', status: 'active', base_price: '49.99', currency: 'USD' },
      { id: 'p2', title: 'Scarf', status: 'active', base_price: '19.99', currency: 'USD' },
    ]),
    listProductUpsells: vi.fn().mockResolvedValue([]),
    createProductUpsell: mocks.createProductUpsell,
    deleteProductUpsell: vi.fn().mockResolvedValue(undefined),
  },
}));

describe('UpsellRulesPage', () => {
  it('renders upsell form and submits', async () => {
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <AuthProvider>
          <ShopProvider>
            <ToastProvider>
              <MemoryRouter>
                <UpsellRulesPage />
              </MemoryRouter>
            </ToastProvider>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await screen.findByRole('option', { name: 'Demo' });
    await waitFor(() => {
      const selects = screen.getAllByRole('combobox');
      expect((selects[1] as HTMLSelectElement).value).toBe('p1');
      expect((selects[2] as HTMLSelectElement).value).toBe('p2');
    });
    await user.click(screen.getByRole('button', { name: /create upsell rule/i }));

    await waitFor(() => {
      expect(mocks.createProductUpsell).toHaveBeenCalledWith(
        's1',
        expect.objectContaining({ source_product_id: 'p1', target_product_id: 'p2' }),
      );
    });
  });
});
