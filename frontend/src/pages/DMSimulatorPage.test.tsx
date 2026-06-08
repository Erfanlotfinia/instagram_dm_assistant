import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import { DMSimulatorPage } from './DMSimulatorPage';

const mocks = vi.hoisted(() => ({
  runDMSimulator: vi.fn().mockResolvedValue({
    conversation_id: 'conv-1',
    message_id: 'msg-1',
    is_simulation: true,
    intent: 'buy_product',
    extracted_slots: { color: 'black' },
    product_resolution: { product_candidates: [] },
    variant_resolution: {},
    inventory_result: {},
    next_state: 'waiting_for_customer_info',
    suggested_reply: 'لطفاً نام و آدرس را بفرستید.',
    auto_send_decision: { auto_send_allowed: false, requires_preview: true },
    handoff_reason: null,
    draft_order: null,
    decision_trace: { intent: 'buy_product' },
  }),
  resetDMSimulator: vi.fn().mockResolvedValue({ deleted_conversations: 2 }),
  listSimulatorRuns: vi.fn().mockResolvedValue([]),
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    listInstagramAccounts: vi.fn().mockResolvedValue([{ id: 'acc-1', username: 'demo_shop', status: 'connected' }]),
    runDMSimulator: mocks.runDMSimulator,
    resetDMSimulator: mocks.resetDMSimulator,
    listSimulatorRuns: mocks.listSimulatorRuns,
  },
}));

describe('DMSimulatorPage', () => {
  it('validates message input and renders simulation result', async () => {
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <AuthProvider>
          <ShopProvider>
            <ToastProvider>
              <MemoryRouter>
                <DMSimulatorPage />
              </MemoryRouter>
            </ToastProvider>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    const runButton = await screen.findByRole('button', { name: /run simulator/i });
    await user.click(runButton);

    await waitFor(() => {
      expect(mocks.runDMSimulator).toHaveBeenCalled();
    });

    expect(await screen.findByText('buy_product')).toBeInTheDocument();
    expect(screen.getByText('لطفاً نام و آدرس را بفرستید.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open simulation conversation' })).toHaveAttribute(
      'href',
      '/conversations/conv-1',
    );
  });

  it('shows reset confirmation before deleting simulation data', async () => {
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <AuthProvider>
          <ShopProvider>
            <ToastProvider>
              <MemoryRouter>
                <DMSimulatorPage />
              </MemoryRouter>
            </ToastProvider>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    const resetButton = await screen.findByRole('button', { name: /reset simulation data/i });
    await user.click(resetButton);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/removes all simulation conversations/i)).toBeInTheDocument();

    const confirmButtons = screen.getAllByRole('button', { name: /reset simulation data/i });
    await user.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() => {
      expect(mocks.resetDMSimulator).toHaveBeenCalledWith('s1');
    });
  });
});
