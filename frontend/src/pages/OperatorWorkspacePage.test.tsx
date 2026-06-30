import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { OperatorWorkspacePage } from './OperatorWorkspacePage';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    refresh: vi.fn().mockResolvedValue({ user: { id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' } }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    listConversations: vi.fn().mockResolvedValue([]),
    listDecisionTraces: vi.fn().mockResolvedValue([]),
    listOrders: vi.fn().mockResolvedValue([]),
    getAnalyticsOperatorPerformance: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
  },
}));

describe('OperatorWorkspacePage', () => {
  it('renders KPI labels and header', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ShopProvider>
            <MemoryRouter>
              <OperatorWorkspacePage />
            </MemoryRouter>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText('Operator Workspace')).toBeInTheDocument();
    });
    // KPI labels also appear as filter <option>s, so use getAllByText.
    expect(screen.getAllByText('Needs attention').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Breached SLA').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Unassigned').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Assigned to me').length).toBeGreaterThan(0);
    expect(screen.getAllByText('High priority').length).toBeGreaterThan(0);
  });

  it('renders empty state when no conversations', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ShopProvider>
            <MemoryRouter>
              <OperatorWorkspacePage />
            </MemoryRouter>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText('No conversations match')).toBeInTheDocument();
    });
  });
});
