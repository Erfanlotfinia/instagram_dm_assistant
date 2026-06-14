import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import {
  AdminAITasksPage,
  AutomationRulesPage,
  OperatorCorrectionsPage,
  ScenarioCoveragePage,
  ScenarioSimulatorPage,
} from './SocialAdminPages';

const mocks = vi.hoisted(() => ({
  listShops: vi.fn().mockResolvedValue([
    { id: 'shop-1', name: 'Demo Shop', slug: 'demo', status: 'active' },
  ]),
  runScenarioRegression: vi.fn().mockResolvedValue({
    automation_handled_rate: 0.5,
    llm_fallback_rate: 0.2,
    handoff_rate: 0.1,
    scenario_accuracy: 0.85,
    reference_resolution_accuracy: 0.9,
    product_discovery_accuracy: 0.88,
    unsafe_action_count: 0,
    false_order_count: 0,
    false_payment_count: 0,
  }),
  getScenarioCoverage: vi.fn().mockResolvedValue([
    {
      scenario_code: 'ASK_PRICE_REFERENCED_PRODUCT',
      scenario_name: 'ask price referenced product',
      description: 'Regression pack covers provider variants.',
      supported_providers: ['instagram', 'whatsapp', 'telegram', 'bale', 'rubika'],
      current_status: 'partially_implemented',
      deterministic_handler_exists: true,
      LLM_fallback_exists: true,
      human_handoff_exists: true,
      tests_exist: true,
      frontend_support_exists: true,
      priority: 'P0',
    },
  ]),
  listAutomationRules: vi.fn().mockResolvedValue([
    {
      order: 7,
      label: 'Structured LLM fallback',
      tier: 'llm',
      detail: 'Only when deterministic layers miss, a constrained LLM returns a schema-validated action.',
    },
  ]),
  listAdminTasks: vi.fn().mockResolvedValue([]),
  createAdminTask: vi.fn().mockResolvedValue({
    id: 'task-1',
    shop_id: 'shop-1',
    requested_by_user_id: 'u1',
    task_type: 'post_caption_draft',
    input_json: { context: 'Summer launch' },
    output_json: { draft: 'Draft post caption draft grounded in Summer launch.', auto_publish: false },
    status: 'completed',
    requires_approval: true,
    approved_by_user_id: null,
    created_at: '2026-06-14T00:00:00Z',
    updated_at: '2026-06-14T00:00:00Z',
  }),
  listOperatorCorrections: vi.fn().mockResolvedValue([]),
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({
      id: 'u1',
      email: 'admin@test.com',
      full_name: 'Admin',
      role: 'owner',
    }),
    listShops: mocks.listShops,
    runScenarioRegression: mocks.runScenarioRegression,
    getScenarioCoverage: mocks.getScenarioCoverage,
    listAutomationRules: mocks.listAutomationRules,
    listAdminTasks: mocks.listAdminTasks,
    createAdminTask: mocks.createAdminTask,
    listOperatorCorrections: mocks.listOperatorCorrections,
  },
}));

function renderWithProviders(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <ShopProvider>
          <ToastProvider>
            <MemoryRouter>{ui}</MemoryRouter>
          </ToastProvider>
        </ShopProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

test('renders scenario coverage page', async () => {
  renderWithProviders(<ScenarioCoveragePage />);
  expect(screen.getByText('Scenario Coverage')).toBeInTheDocument();
  await waitFor(() => expect(mocks.getScenarioCoverage).toHaveBeenCalledWith('shop-1'));
  expect(await screen.findByText('ask price referenced product')).toBeInTheDocument();
});

test('renders automation rules priority', async () => {
  renderWithProviders(<AutomationRulesPage />);
  expect(await screen.findByText('Structured LLM fallback')).toBeInTheDocument();
  await waitFor(() => expect(mocks.listAutomationRules).toHaveBeenCalledWith('shop-1'));
});

test('renders scenario simulator pack', async () => {
  renderWithProviders(<ScenarioSimulatorPage />);
  expect(screen.getByText('Run scenario pack')).toBeInTheDocument();
  await waitFor(() => expect(mocks.listShops).toHaveBeenCalled());
});

test('run scenario pack calls regression API', async () => {
  const user = userEvent.setup();
  renderWithProviders(<ScenarioSimulatorPage />);

  const runButton = screen.getByRole('button', { name: 'Run scenario pack' });
  await waitFor(() => expect(runButton).toBeEnabled());

  await user.click(runButton);

  await waitFor(() => expect(mocks.runScenarioRegression).toHaveBeenCalledWith('shop-1'));
  expect(await screen.findByText('Regression results')).toBeInTheDocument();
  expect(screen.getByText('Scenario accuracy (handler match)')).toBeInTheDocument();
});

test('renders admin AI tasks approval gate', () => {
  renderWithProviders(<AdminAITasksPage />);
  expect(screen.getByText(/requires admin approval/i)).toBeInTheDocument();
});

test('renders operator corrections', () => {
  renderWithProviders(<OperatorCorrectionsPage />);
  expect(screen.getByText(/Capture correction/)).toBeInTheDocument();
});
