import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import { ConversationDetailPage } from './ConversationDetailPage';

const mocks = vi.hoisted(() => ({
  takeOver: vi.fn().mockResolvedValue({ conversation_id: 'c1', handoff_required: true }),
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    getConversation: vi.fn().mockResolvedValue({
      id: 'c1',
      shop_id: 's1',
      state: 'pending_handoff',
      handoff_required: true,
      messages: [],
      agent_runs: [],
      agent_actions: [],
    }),
    takeOverConversation: mocks.takeOver,
  },
}));

describe('ConversationDetailPage', () => {
  it('allows operator to take over conversation', async () => {
    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ShopProvider>
            <ToastProvider>
              <MemoryRouter initialEntries={['/conversations/c1?shopId=s1']}>
                <Routes>
                  <Route path="/conversations/:conversationId" element={<ConversationDetailPage />} />
                </Routes>
              </MemoryRouter>
            </ToastProvider>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    const button = await screen.findByRole('button', { name: /take over/i });
    await user.click(button);

    await waitFor(() => {
      expect(mocks.takeOver).toHaveBeenCalledWith('s1', 'c1');
    });
  });
});
