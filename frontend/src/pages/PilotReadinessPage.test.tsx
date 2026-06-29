import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import { PilotReadinessPage } from './PilotReadinessPage';

const mocks = vi.hoisted(() => {
  const state = { emergency_stop_enabled: true };
  const pilotSettings = () => ({
    shop_id: 's1',
    pilot_enabled: true,
    pilot_name: 'June Pilot',
    pilot_start_date: null,
    pilot_end_date: null,
    max_auto_sent_messages_per_day: 10,
    max_auto_created_orders_per_day: 5,
    require_operator_approval_for_first_50_orders: true,
    allowed_instagram_account_ids: ['ig1'],
    allowed_product_ids: null,
    emergency_stop_enabled: state.emergency_stop_enabled,
    created_at: '2026-06-09T00:00:00Z',
    updated_at: '2026-06-09T00:00:00Z',
  });
  return {
    state,
    pilotSettings,
    activatePilotModeEmergencyStop: vi.fn(),
    resumePilot: vi.fn(),
  };
});

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    getPilotReadiness: vi.fn().mockImplementation(async () => ({
      shop_id: 's1',
      ready_for_trl6_pilot: false,
      latest_trl_validation: { status: 'failed' },
      pilot_settings: mocks.pilotSettings(),
      warnings: ['Latest TRL validation run passed thresholds'],
      checklist: [
        { key: 'instagram_webhook_connected', label: 'Instagram webhook connected', passed: true, detail: null },
        { key: 'inventory_verified', label: 'Inventory verified', passed: false, detail: 'stale' },
      ],
      criteria: [
        { key: 'latest_trl_validation', label: 'Latest TRL validation run passed thresholds', passed: false, detail: 'failed' },
        { key: 'emergency_stop_tested', label: 'Emergency stop tested', passed: true, detail: null },
      ],
    })),
    getPilotMetrics: vi.fn().mockResolvedValue({
      inbound_messages: 12,
      auto_sent_messages: 4,
      previewed_messages: 3,
      human_handoff_count: 2,
      draft_orders: 1,
      confirmed_orders: 1,
      paid_orders: 1,
      cancelled_orders: 0,
      failed_jobs: 1,
      invalid_llm_outputs: 0,
      average_response_time_ms: 500,
      p95_response_time_ms: 900,
      operator_takeover_count: 1,
    }),
    getPilotEvents: vi.fn().mockResolvedValue({
      events: [
        {
          id: 'e1',
          shop_id: 's1',
          event_type: 'emergency_stop',
          severity: 'critical',
          title: 'Emergency stop activated',
          description: 'Stopped',
          metadata: null,
          created_at: '2026-06-09T00:00:00Z',
        },
      ],
    }),
    activatePilotModeEmergencyStop: mocks.activatePilotModeEmergencyStop.mockImplementation(async () => {
      mocks.state.emergency_stop_enabled = true;
      return {
        pilot_settings: mocks.pilotSettings(),
        event: {},
        scope_preview: {
          active_conversation_count: 2,
          simulation_conversation_count: 1,
          affected_conversation_ids: ['c1', 'c2'],
        },
        incident_id: 'inc-1',
      };
    }),
    resumePilot: mocks.resumePilot.mockImplementation(async () => {
      mocks.state.emergency_stop_enabled = false;
      return { pilot_settings: mocks.pilotSettings(), event: {} };
    }),
  },
}));

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ShopProvider>
          <ToastProvider>
            <MemoryRouter>
              <PilotReadinessPage />
            </MemoryRouter>
          </ToastProvider>
        </ShopProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('PilotReadinessPage', () => {
  it('renders readiness checklist, metrics, events, and warning banners', async () => {
    renderPage();

    expect(await screen.findByRole('heading', { name: /trl 6 pilot readiness/i })).toBeInTheDocument();
    expect(await screen.findByText(/pilot mode active/i)).toBeInTheDocument();
    expect(screen.getByText(/auto-send and auto-order progression are disabled/i)).toBeInTheDocument();
    expect(screen.getByText(/validation outdated/i)).toBeInTheDocument();
    expect(screen.getByText(/failed jobs present/i)).toBeInTheDocument();
    expect(screen.getByText(/Instagram webhook connected/i)).toBeInTheDocument();
    // "Inventory verified" appears in both the new PilotChecklistPanel (missing
    // requirements) and the existing operational checklist panel.
    expect(screen.getAllByText(/Inventory verified/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Inbound messages/i)).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText(/Emergency stop activated/i)).toBeInTheDocument();
    expect(screen.getByText(/Readiness assessment/i)).toBeInTheDocument();
  });

  it('runs emergency stop through confirm dialog and resume flow', async () => {
    const user = userEvent.setup();
    renderPage();

    const resumeButton = await screen.findByRole('button', { name: /^resume pilot$/i });
    await user.click(resumeButton);
    await waitFor(() => expect(mocks.resumePilot).toHaveBeenCalledWith('s1'));

    const stopButton = await screen.findByRole('button', { name: /^emergency stop$/i });
    await waitFor(() => expect(stopButton).not.toBeDisabled());
    await user.click(stopButton);
    await user.click(await screen.findByRole('button', { name: /activate emergency stop/i }));
    await waitFor(() => expect(mocks.activatePilotModeEmergencyStop).toHaveBeenCalledWith('s1', undefined));
  });
});
