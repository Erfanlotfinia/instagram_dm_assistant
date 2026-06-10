import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ShopProvider } from '../../contexts/ShopContext';
import { ToastProvider } from '../../contexts/ToastContext';
import { ReplayPanel } from './ReplayPanel';

const mocks = vi.hoisted(() => ({
  runReplay: vi.fn(),
  listReplayRuns: vi.fn().mockResolvedValue([]),
  listScenarioPacks: vi.fn().mockResolvedValue([]),
  createScenarioPack: vi.fn(),
}));

vi.mock('../../contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuth: () => ({ user: { id: 'u1' }, isAuthenticated: true }),
}));

vi.mock('../../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    runReplay: mocks.runReplay,
    listReplayRuns: mocks.listReplayRuns,
    listScenarioPacks: mocks.listScenarioPacks,
    createScenarioPack: mocks.createScenarioPack,
  },
}));

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ShopProvider>
        <ToastProvider>
          <ReplayPanel />
        </ToastProvider>
      </ShopProvider>
    </QueryClientProvider>,
  );
}

describe('ReplayPanel', () => {
  it('runs golden replay pack', async () => {
    mocks.runReplay.mockResolvedValue({
      run: {
        id: 'run-1',
        passed_items: 3,
        total_items: 3,
        failed_items: 0,
        catalog_snapshot_hash: 'abc123',
        items: [],
      },
    });

    const user = userEvent.setup();
    renderPanel();

    const runButton = await screen.findByRole('button', { name: /run golden replay pack/i });
    await waitFor(() => expect(runButton).toBeEnabled());
    await user.click(runButton);

    await waitFor(() => {
      expect(mocks.runReplay).toHaveBeenCalledWith(
        's1',
        expect.objectContaining({
          scenarios: expect.arrayContaining([expect.objectContaining({ item_key: 'ask-price' })]),
        }),
      );
    });
  });

  it('saves scenario pack from golden scenarios', async () => {
    mocks.createScenarioPack.mockResolvedValue({
      id: 'pack-1',
      name: 'Golden replay pack',
      scenarios_json: [{ item_key: 'ask-price' }],
    });

    const user = userEvent.setup();
    renderPanel();

    const saveButton = await screen.findByRole('button', { name: /save golden pack/i });
    await waitFor(() => expect(saveButton).toBeEnabled());
    await user.click(saveButton);

    await waitFor(() => {
      expect(mocks.createScenarioPack).toHaveBeenCalledWith(
        's1',
        expect.objectContaining({ is_golden: true, pack_type: 'handcrafted' }),
      );
    });
  });
});
