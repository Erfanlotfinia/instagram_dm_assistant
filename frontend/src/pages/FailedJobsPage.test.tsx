import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import { FailedJobsPage } from './FailedJobsPage';

const mocks = vi.hoisted(() => ({
  listFailedJobs: vi.fn(),
  retryFailedJob: vi.fn(),
  ignoreFailedJob: vi.fn(),
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active', default_currency: 'USD', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }]),
    listFailedJobs: mocks.listFailedJobs,
    retryFailedJob: mocks.retryFailedJob,
    ignoreFailedJob: mocks.ignoreFailedJob,
  },
}));

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ShopProvider>
          <ToastProvider>
            <FailedJobsPage />
          </ToastProvider>
        </ShopProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('FailedJobsPage', () => {
  it('renders failed job list with redacted payload', async () => {
    mocks.listFailedJobs.mockResolvedValue({
      items: [
        {
          id: 'job-1',
          shop_id: 's1',
          queue_name: 'instagram.message.received',
          job_type: 'message_received',
          redacted_payload: { shop_id: 's1', access_token: '[REDACTED]' },
          error_message: 'boom',
          traceback: null,
          retry_count: 1,
          max_retries: 3,
          status: 'failed',
          created_at: '2026-06-08T00:00:00Z',
          updated_at: '2026-06-08T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 25,
    });

    renderPage();
    expect(await screen.findByText('instagram.message.received')).toBeInTheDocument();
    expect(screen.getByText('View redacted payload')).toBeInTheDocument();
  });

  it('retries failed job after confirmation', async () => {
    mocks.listFailedJobs.mockResolvedValue({
      items: [
        {
          id: 'job-1',
          shop_id: 's1',
          queue_name: 'instagram.message.received',
          job_type: 'message_received',
          redacted_payload: {},
          error_message: 'boom',
          traceback: null,
          retry_count: 1,
          max_retries: 3,
          status: 'failed',
          created_at: '2026-06-08T00:00:00Z',
          updated_at: '2026-06-08T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 25,
    });
    mocks.retryFailedJob.mockResolvedValue({ id: 'job-1', status: 'retried', message: 'ok' });

    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Retry' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(within(dialog).getByRole('button', { name: 'Retry' }));
    await waitFor(() => expect(mocks.retryFailedJob).toHaveBeenCalledWith('s1', 'job-1'));
  });
});
