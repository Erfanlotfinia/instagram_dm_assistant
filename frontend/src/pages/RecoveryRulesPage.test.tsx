import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import { RecoveryRulesPage } from './RecoveryRulesPage';

const mocks = vi.hoisted(() => ({
  createRecoveryRule: vi.fn().mockResolvedValue({ id: 'r1' }),
  listRecoveryRules: vi.fn().mockResolvedValue([]),
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    listRecoveryRules: mocks.listRecoveryRules,
    createRecoveryRule: mocks.createRecoveryRule,
    deleteRecoveryRule: vi.fn().mockResolvedValue(undefined),
  },
}));

describe('RecoveryRulesPage', () => {
  it('renders recovery rules form and submits', async () => {
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <AuthProvider>
          <ShopProvider>
            <ToastProvider>
              <MemoryRouter>
                <RecoveryRulesPage />
              </MemoryRouter>
            </ToastProvider>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await screen.findByRole('button', { name: /create recovery rule/i });
    await user.click(screen.getByRole('button', { name: /create recovery rule/i }));

    await waitFor(() => {
      expect(mocks.createRecoveryRule).toHaveBeenCalledWith(
        's1',
        expect.objectContaining({ trigger_after_minutes: 60, max_attempts: 3 }),
      );
    });
  });
});
