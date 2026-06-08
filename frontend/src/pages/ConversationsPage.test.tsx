import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ConversationsPage } from './ConversationsPage';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    listConversations: vi.fn().mockResolvedValue([
      {
        id: 'c1',
        shop_id: 's1',
        customer_id: 'cust-1',
        state: 'open',
        handoff_required: true,
        preview_required: true,
        agent_mode: 'human_first',
        priority_level: 'urgent',
        priority_score: 85,
        needs_attention: true,
        customer: { id: 'cust-1', instagram_user_id: 'ig-1', full_name: 'Ali' },
        linked_product: { id: 'p1', title: 'Hoodie' },
        linked_order: { id: 'o1', status: 'waiting_for_payment', payment_status: 'pending', total_amount: '49.99' },
        assigned_operator: { id: 'u1', full_name: 'Admin' },
        last_message_text: 'Hello',
        confidence_score: 0.85,
        updated_at: '2026-06-07T10:00:00Z',
        created_at: '2026-06-07T09:00:00Z',
      },
    ]),
  },
}));

describe('ConversationsPage', () => {
  it('renders priority badge and enriched list columns', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ShopProvider>
            <MemoryRouter>
              <ConversationsPage />
            </MemoryRouter>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Ali' })).toBeInTheDocument();
      expect(screen.getByText('urgent (85)')).toBeInTheDocument();
      expect(screen.getByText('Hoodie')).toBeInTheDocument();
      expect(screen.getByText('waiting_for_payment')).toBeInTheDocument();
      expect(screen.getByText('Admin')).toBeInTheDocument();
    });
  });

  it('toggles urgent filter chip', async () => {
    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ShopProvider>
            <MemoryRouter>
              <ConversationsPage />
            </MemoryRouter>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByRole('button', { name: 'Urgent' })).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: 'Urgent' }));
    expect(screen.getByRole('button', { name: 'Urgent' })).toHaveAttribute('aria-pressed', 'true');
  });
});
