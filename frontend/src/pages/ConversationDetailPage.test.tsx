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
  approve: vi.fn().mockResolvedValue({ id: 'r1', status: 'sent' }),
  edit: vi.fn().mockResolvedValue({ id: 'r1', status: 'sent' }),
  reject: vi.fn().mockResolvedValue({ id: 'r1', status: 'rejected' }),
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
      suggested_replies: [{ id: 'r1', shop_id: 's1', conversation_id: 'c1', message_id: null, suggested_text: 'Try the black dress?', status: 'pending', generated_by: 'agent', approved_by_user_id: null, edited_text: null, reason: 'low confidence', created_at: '2026-06-08T00:00:00Z', updated_at: '2026-06-08T00:00:00Z' }],
    }),
    takeOverConversation: mocks.takeOver,
    releaseConversationToAgent: vi.fn(),
    markConversationResolved: vi.fn(),
    updateConversationCustomer: vi.fn(),
    createOrderFromConversation: vi.fn(),
    sendConversationMessage: vi.fn(),
    approveSuggestedReply: mocks.approve,
    editAndSendSuggestedReply: mocks.edit,
    rejectSuggestedReply: mocks.reject,
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

  it('shows suggested reply card and supports approve, edit, and reject actions', async () => {
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

    expect(await screen.findByLabelText(/suggested reply card/i)).toBeInTheDocument();
    await user.clear(screen.getByLabelText(/edit before sending/i));
    await user.type(screen.getByLabelText(/edit before sending/i), 'Edited reply');
    await waitFor(() => expect(screen.getByLabelText(/edit before sending/i)).toHaveValue('Edited reply'));
    await user.click(screen.getByRole('button', { name: /edit and send/i }));
    await user.click(screen.getByRole('button', { name: /approve and send/i }));
    await user.click(screen.getByRole('button', { name: /reject/i }));

    await waitFor(() => {
      expect(mocks.approve).toHaveBeenCalledWith('s1', 'r1');
      expect(mocks.edit).toHaveBeenCalledWith('s1', 'r1', 'Edited reply');
      expect(mocks.reject).toHaveBeenCalledWith('s1', 'r1', 'Rejected by operator');
    });
  });
});
