import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastContainer, ToastProvider } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import { SystemHealthPage } from './SystemHealthPage';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    getReady: vi.fn().mockResolvedValue({
      status: 'degraded',
      checks: {
        postgres: 'ok',
        redis: 'ok',
        rabbitmq: 'error',
        qdrant: 'ok',
        openai_config: 'ok',
      },
    }),
    listAccessibleFailedJobs: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'job-1',
          shop_id: null,
          queue_name: 'instagram.message.received.dlq',
          job_type: 'message_received',
          payload: {},
          error_message: 'demo: Worker payload failed JSON schema validation',
          traceback: 'ValidationError: message_id field required',
          retry_count: 3,
          max_retries: 3,
          status: 'failed',
          created_at: '2026-06-08T12:00:00Z',
          updated_at: '2026-06-08T12:00:00Z',
        },
        {
          id: 'job-2',
          shop_id: 's1',
          queue_name: 'instagram.message.received',
          job_type: 'message_received',
          payload: {},
          error_message: 'demo: ConversationOrchestrator timed out waiting for OpenAI response',
          traceback: 'TimeoutError: LLM request exceeded 30s',
          retry_count: 3,
          max_retries: 3,
          status: 'failed',
          created_at: '2026-06-08T11:48:00Z',
          updated_at: '2026-06-08T11:48:00Z',
        },
      ],
      total: 2,
      page: 1,
      page_size: 25,
    }),
    retryFailedJobById: vi.fn().mockResolvedValue({ id: 'job-1', status: 'retried', message: 'Job requeued' }),
    ignoreFailedJobById: vi.fn().mockResolvedValue({ id: 'job-1', status: 'ignored', message: 'Job ignored' }),
  },
}));

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AuthProvider>
        <ShopProvider>
          <ToastProvider>
            <MemoryRouter>
              <SystemHealthPage />
              <ToastContainer />
            </MemoryRouter>
          </ToastProvider>
        </ShopProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('SystemHealthPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders readiness checks and failed job cards', async () => {
    renderPage();

    expect(await screen.findByText(/Overall status: degraded/)).toBeInTheDocument();
    expect(screen.getByText('2 waiting')).toBeInTheDocument();
    expect(screen.getAllByText('Unscoped').length).toBeGreaterThan(0);
    expect(
      await screen.findByText('demo: Worker payload failed JSON schema validation'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('demo: ConversationOrchestrator timed out waiting for OpenAI response'),
    ).toBeInTheDocument();
  });

  it('retries a failed job and shows traceback', async () => {
    renderPage();

    await screen.findByText('demo: Worker payload failed JSON schema validation');
    await userEvent.click(screen.getAllByRole('button', { name: 'Show traceback' })[0]);
    expect(screen.getByText('ValidationError: message_id field required')).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole('button', { name: 'Retry' })[0]);
    await waitFor(() => {
      expect(apiClient.retryFailedJobById).toHaveBeenCalledWith('job-1');
    });
    expect(await screen.findByText('Failed job requeued')).toBeInTheDocument();
  });

  it('filters failed jobs with shop chips', async () => {
    renderPage();

    expect(await screen.findByRole('button', { name: 'All shops' })).toHaveAttribute('aria-pressed', 'true');
    expect(
      screen.getByText(/Showing failed jobs from all accessible shops/),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Unscoped' }));
    await waitFor(() => {
      expect(apiClient.listAccessibleFailedJobs).toHaveBeenCalledWith({
        shopId: undefined,
        unscopedOnly: true,
        page: 1,
      });
    });
    expect(
      screen.getByText(/Showing unscoped worker failures only/),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Demo' }));
    await waitFor(() => {
      expect(apiClient.listAccessibleFailedJobs).toHaveBeenCalledWith({
        shopId: 's1',
        unscopedOnly: false,
        page: 1,
      });
    });
    expect(screen.getByText(/Showing failed jobs for Demo only/)).toBeInTheDocument();
  });
});
