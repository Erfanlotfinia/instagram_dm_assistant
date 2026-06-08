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
  updateCustomer: vi.fn().mockResolvedValue({ id: 'cust-1', full_name: 'Sara' }),
  sendPaymentLink: vi.fn().mockResolvedValue({ id: 'o1', status: 'waiting_for_payment' }),
  baseConversation: {
  id: 'c1',
  shop_id: 's1',
  instagram_account_id: 'ia1',
  customer_id: 'cust-1',
  state: 'pending_handoff',
  workflow_state: 'human_handoff',
  agent_paused: true,
  handoff_required: true,
  handoff_reason: 'low confidence',
  last_intent: null,
  assigned_operator_id: 'u1',
  last_message_at: '2026-06-08T00:00:00Z',
  created_at: '2026-06-08T00:00:00Z',
  updated_at: '2026-06-08T00:00:00Z',
  priority_level: 'high',
  priority_score: 55,
  messages: [
    {
      id: 'm1',
      conversation_id: 'c1',
      direction: 'inbound',
      message_type: 'text',
      text: 'I want this dress',
      created_at: '2026-06-08T00:00:00Z',
    },
  ],
  events: [
    {
      id: 'e1',
      conversation_id: 'c1',
      event_type: 'inbound_message_received',
      title: 'Inbound message received',
      description: 'I want this dress',
      metadata: null,
      created_by_user_id: null,
      created_at: '2026-06-08T00:00:00Z',
    },
  ],
  customer_profile: {
    id: 'cust-1',
    instagram_user_id: 'ig-1',
    full_name: 'Ali',
    phone: '0912',
    city: 'Tehran',
    address: null,
    postal_code: null,
    notes: null,
    previous_orders: [],
    preferred_size: 'M',
    preferred_colors: ['black'],
    last_purchase_at: null,
    total_paid_amount: '0',
    order_count: 0,
    is_repeat_customer: false,
  },
  linked_order: {
    id: 'o1',
    status: 'waiting_for_payment',
    payment_status: 'pending',
    total_amount: '99.00',
  },
  agent_runs: [],
  agent_actions: [],
  suggested_replies: [
    {
      id: 'r1',
      shop_id: 's1',
      conversation_id: 'c1',
      message_id: null,
      suggested_text: 'Try the black dress?',
      status: 'pending',
      generated_by: 'agent',
      approved_by_user_id: null,
      edited_text: null,
      reason: 'low confidence',
      created_at: '2026-06-08T00:00:00Z',
      updated_at: '2026-06-08T00:00:00Z',
    },
  ],
  },
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    getConversation: vi.fn().mockResolvedValue(mocks.baseConversation),
    takeOverConversation: mocks.takeOver,
    releaseConversationToAgent: vi.fn(),
    markConversationResolved: vi.fn(),
    updateConversationCustomer: mocks.updateCustomer,
    createOrderFromConversation: vi.fn(),
    sendConversationMessage: vi.fn(),
    sendPaymentLink: mocks.sendPaymentLink,
    markOrderPaid: vi.fn(),
    sendTrackingCode: vi.fn(),
    cancelOrder: vi.fn(),
    approveSuggestedReply: mocks.approve,
    editAndSendSuggestedReply: mocks.edit,
    rejectSuggestedReply: mocks.reject,
  },
}));

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
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
}

describe('ConversationDetailPage', () => {
  it('allows operator to take over conversation', async () => {
    const user = userEvent.setup();
    renderPage();

    const button = await screen.findByRole('button', { name: /take over/i });
    await user.click(button);

    await waitFor(() => {
      expect(mocks.takeOver).toHaveBeenCalledWith('s1', 'c1');
    });
  });

  it('renders message timeline and conversation events', async () => {
    renderPage();
    expect(await screen.findByRole('heading', { name: 'Message timeline' })).toBeInTheDocument();
    expect(screen.getAllByText('I want this dress').length).toBeGreaterThan(0);
    expect(screen.getByText('Inbound message received')).toBeInTheDocument();
  });

  it('shows suggested reply card and supports approve, edit, and reject actions', async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByLabelText(/suggested reply card/i)).toBeInTheDocument();
    await user.clear(screen.getByLabelText(/edit before sending/i));
    await user.type(screen.getByLabelText(/edit before sending/i), 'Edited reply');
    await user.click(screen.getByRole('button', { name: /edit and send/i }));
    await user.click(screen.getByRole('button', { name: /approve and send/i }));
    await user.click(screen.getByRole('button', { name: /reject/i }));

    await waitFor(() => {
      expect(mocks.approve).toHaveBeenCalledWith('s1', 'r1');
      expect(mocks.edit).toHaveBeenCalledWith('s1', 'r1', 'Edited reply');
      expect(mocks.reject).toHaveBeenCalledWith('s1', 'r1', 'Rejected by operator');
    });
  });

  it('saves customer profile and triggers payment link quick action', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.clear(await screen.findByLabelText('Full name'));
    await user.type(screen.getByLabelText('Full name'), 'Sara');
    await user.click(screen.getByRole('button', { name: /save customer/i }));
    await user.click(screen.getByRole('button', { name: /send payment link/i }));

    await waitFor(() => {
      expect(mocks.updateCustomer).toHaveBeenCalled();
      expect(mocks.sendPaymentLink).toHaveBeenCalledWith('s1', 'o1');
    });
  });
});
