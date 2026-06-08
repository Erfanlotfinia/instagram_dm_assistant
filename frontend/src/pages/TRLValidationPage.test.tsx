import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import { TRLValidationPage } from './TRLValidationPage';

const mocks = vi.hoisted(() => ({
  listTRLValidationRuns: vi.fn().mockResolvedValue([{ id: 'run-1', shop_id: 's1', status: 'completed', total_scenarios: 2, passed_scenarios: 1, failed_scenarios: 1, metrics_json: { intent_accuracy: 0.95, slot_extraction_accuracy: 0.9, product_resolution_accuracy: 1, variant_resolution_accuracy: 0.9, false_auto_send_count: 0, false_order_creation_count: 0, thresholds_passed: { intent_accuracy: true } }, started_at: '2026-06-08T00:00:00Z', completed_at: '2026-06-08T00:00:01Z', created_by_user_id: null }]),
  listTRLValidationScenarios: vi.fn().mockResolvedValue([{ id: 'result-1', run_id: 'run-1', scenario_id: 'TRL-001', input_json: { message_text: 'سلام' }, expected_json: { intent: 'buy_product' }, actual_json: { intent: 'unclear', state: 'idle' }, passed: false, failure_reasons: ['intent mismatch'], processing_time_ms: 12, conversation_id: 'conv-1', order_id: null, created_at: '2026-06-08T00:00:01Z' }]),
  runTRLValidation: vi.fn().mockResolvedValue({ id: 'run-2', shop_id: 's1', status: 'completed', total_scenarios: 1, passed_scenarios: 1, failed_scenarios: 0, metrics_json: {}, started_at: '', completed_at: '', created_by_user_id: null }),
  resetTRLValidation: vi.fn().mockResolvedValue({ deleted_runs: 1, deleted_conversations: 2, deleted_orders: 0 }),
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    listTRLValidationRuns: mocks.listTRLValidationRuns,
    listTRLValidationScenarios: mocks.listTRLValidationScenarios,
    runTRLValidation: mocks.runTRLValidation,
    resetTRLValidation: mocks.resetTRLValidation,
  },
}));

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AuthProvider><ShopProvider><ToastProvider><MemoryRouter><TRLValidationPage /></MemoryRouter></ToastProvider></ShopProvider></AuthProvider>
    </QueryClientProvider>,
  );
}

describe('TRLValidationPage', () => {
  it('renders latest run summary and scenario table', async () => {
    renderPage();
    expect(await screen.findByText('TRL 5 Validation')).toBeInTheDocument();
    expect(await screen.findByText('Latest run summary')).toBeInTheDocument();
    expect(await screen.findByText('TRL-001')).toBeInTheDocument();
  });

  it('run validation button works with mocked API', async () => {
    renderPage();
    await userEvent.click(await screen.findByRole('button', { name: /run validation/i }));
    await waitFor(() => expect(mocks.runTRLValidation).toHaveBeenCalled());
  });

  it('failed scenario detail renders', async () => {
    renderPage();
    await userEvent.click(await screen.findByText('TRL-001'));
    expect(await screen.findByText(/Failed scenario detail/)).toBeInTheDocument();
    expect(screen.getByText(/intent mismatch/)).toBeInTheDocument();
  });

  it('loading/error/empty states', async () => {
    mocks.listTRLValidationRuns.mockRejectedValueOnce(new Error('boom'));
    renderPage();
    expect(screen.getByText(/Select a shop|Loading TRL validation/)).toBeInTheDocument();
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
  });
});
