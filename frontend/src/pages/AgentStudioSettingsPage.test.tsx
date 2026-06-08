import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import { AgentStudioSettingsPage } from './AgentStudioSettingsPage';

const mocks = vi.hoisted(() => ({
  updateAgentStudioSettings: vi.fn().mockResolvedValue({}),
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    getAgentStudioSettings: vi.fn().mockResolvedValue({
      shop_id: 's1',
      mode: 'copilot',
      auto_send_enabled: false,
      preview_required_for_low_confidence: true,
      preview_required_for_first_order: true,
      preview_required_for_high_value_order: true,
      confidence_threshold_intent: '0.75',
      confidence_threshold_product: '0.80',
      confidence_threshold_variant: '0.85',
      confidence_threshold_address: '0.80',
      high_value_order_threshold: '500',
      brand_voice: 'Warm and concise',
      selling_style: 'friendly',
      discount_policy_json: {},
      handoff_policy_json: {},
    }),
    updateAgentStudioSettings: mocks.updateAgentStudioSettings,
  },
}));

describe('AgentStudioSettingsPage', () => {
  it('renders mode selector and saves settings form', async () => {
    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ShopProvider>
            <ToastProvider>
              <MemoryRouter>
                <AgentStudioSettingsPage />
              </MemoryRouter>
            </ToastProvider>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await screen.findByDisplayValue('Warm and concise');
    const selector = await screen.findByLabelText(/mode selector/i);
    expect(selector).toBeInTheDocument();
    await user.selectOptions(selector, 'controlled_autopilot');
    await waitFor(() => expect(selector).toHaveValue('controlled_autopilot'));
    await user.click(screen.getByRole('button', { name: /save agent settings/i }));

    await waitFor(() => {
      expect(mocks.updateAgentStudioSettings).toHaveBeenCalledWith('s1', expect.objectContaining({ mode: 'controlled_autopilot' }));
    });
  });
});
