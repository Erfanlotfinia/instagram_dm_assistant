import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import { ToastProvider } from '../../contexts/ToastContext';
import { TelegramConnectCard } from './TelegramConnectCard';
import type { ChannelAccount } from '../../types/channel';

const mocks = vi.hoisted(() => ({
  startTelegramConnect: vi.fn(),
  getTelegramConnectSession: vi.fn(),
  submitTelegramBotToken: vi.fn(),
  completeTelegramConnect: vi.fn(),
  cancelTelegramConnect: vi.fn(),
  disconnectChannel: vi.fn(),
  refreshTelegramBusiness: vi.fn(),
  reconnectTelegramBusiness: vi.fn(),
  rotateTelegramManagedBotToken: vi.fn(),
  reconnectTelegramManagedBot: vi.fn(),
}));

vi.mock('../../services/apiClient', () => ({
  apiClient: {
    startTelegramConnect: mocks.startTelegramConnect,
    getTelegramConnectSession: mocks.getTelegramConnectSession,
    submitTelegramBotToken: mocks.submitTelegramBotToken,
    completeTelegramConnect: mocks.completeTelegramConnect,
    cancelTelegramConnect: mocks.cancelTelegramConnect,
    disconnectChannel: mocks.disconnectChannel,
    refreshTelegramBusiness: mocks.refreshTelegramBusiness,
    reconnectTelegramBusiness: mocks.reconnectTelegramBusiness,
    rotateTelegramManagedBotToken: mocks.rotateTelegramManagedBotToken,
    reconnectTelegramManagedBot: mocks.reconnectTelegramManagedBot,
  },
}));

function makeManagedAccount(overrides: Partial<ChannelAccount> = {}): ChannelAccount {
  return {
    id: 'ca-telegram',
    shop_id: 's1',
    provider: 'telegram',
    display_name: 'Telegram',
    status: 'webhook_configured',
    capabilities_json: {},
    settings_json: {},
    connection_mode: 'bot',
    managed_bot: true,
    manager_bot_id: '999',
    managed_bot_id: '888001',
    bot_username: 'modira_shop_bot',
    bot_token_configured: true,
    token_configured: false,
    webhook_secret_configured: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function renderCard(props: {
  account?: ChannelAccount | null;
  canManage?: boolean;
  onRefresh?: () => void;
}) {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <TelegramConnectCard
          shopId="s1"
          account={props.account ?? null}
          canManage={props.canManage ?? true}
          onRefresh={props.onRefresh ?? vi.fn()}
        />
      </ToastProvider>
    </MemoryRouter>,
  );
}

describe('TelegramConnectCard managed bot', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.startTelegramConnect.mockResolvedValue({
      session_id: 'sess-1',
      expires_at: '2026-12-31T00:00:00Z',
      status: 'waiting_managed_bot_approval',
      deep_link: 'https://t.me/newbot/modira_manager/modira_shop_bot?name=Telegram',
      suggested_bot_username: 'modira_shop_bot',
      managed_bot: true,
    });
    mocks.getTelegramConnectSession.mockResolvedValue({
      id: 'sess-1',
      shop_id: 's1',
      mode: 'bot',
      status: 'waiting_managed_bot_approval',
      expires_at: '2026-12-31T00:00:00Z',
      deep_link: 'https://t.me/newbot/modira_manager/modira_shop_bot?name=Telegram',
      suggested_bot_username: 'modira_shop_bot',
      managed_bot: true,
      metadata_json: {},
    });
    mocks.cancelTelegramConnect.mockResolvedValue({});
    mocks.rotateTelegramManagedBotToken.mockResolvedValue(makeManagedAccount());
    mocks.reconnectTelegramManagedBot.mockResolvedValue(makeManagedAccount());
  });

  it('renders Create Bot when not connected', () => {
    renderCard({});
    expect(screen.getByRole('button', { name: 'Create Bot' })).toBeInTheDocument();
  });

  it('starts managed session and shows deep link', async () => {
    const user = userEvent.setup();
    renderCard({});

    await user.click(screen.getByRole('button', { name: 'Create Bot' }));

    await waitFor(() => {
      expect(mocks.startTelegramConnect).toHaveBeenCalledWith('s1', {
        mode: 'bot',
        display_name: 'Telegram',
        channel_account_id: undefined,
        managed_bot: true,
      });
    });

    expect(await screen.findByRole('link', { name: 'Open in Telegram' })).toHaveAttribute(
      'href',
      'https://t.me/newbot/modira_manager/modira_shop_bot?name=Telegram',
    );
    expect(screen.queryByLabelText('Bot token')).not.toBeInTheDocument();
  });

  it('reveals advanced token form when requested', async () => {
    const user = userEvent.setup();
    mocks.startTelegramConnect.mockResolvedValueOnce({
      session_id: 'sess-2',
      expires_at: '2026-12-31T00:00:00Z',
      status: 'waiting_bot_token',
    });
    mocks.getTelegramConnectSession.mockResolvedValueOnce({
      id: 'sess-2',
      shop_id: 's1',
      mode: 'bot',
      status: 'waiting_bot_token',
      expires_at: '2026-12-31T00:00:00Z',
      metadata_json: {},
    });

    renderCard({});
    await user.click(screen.getByRole('button', { name: 'Advanced: paste bot token' }));

    await waitFor(() => {
      expect(mocks.startTelegramConnect).toHaveBeenCalledWith('s1', {
        mode: 'bot',
        display_name: 'Telegram',
        channel_account_id: undefined,
      });
    });
    expect(await screen.findByLabelText('Bot token')).toBeInTheDocument();
  });

  it('shows Rotate Token and Reconnect for connected managed account', () => {
    renderCard({ account: makeManagedAccount() });
    expect(screen.getByRole('button', { name: 'Rotate Token' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reconnect' })).toBeInTheDocument();
    expect(screen.queryByLabelText('Bot token')).not.toBeInTheDocument();
    expect(screen.getByText('Managed')).toBeInTheDocument();
  });

  it('calls rotate endpoint for managed account', async () => {
    const user = userEvent.setup();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    renderCard({ account: makeManagedAccount() });

    await user.click(screen.getByRole('button', { name: 'Rotate Token' }));

    await waitFor(() => {
      expect(mocks.rotateTelegramManagedBotToken).toHaveBeenCalledWith('s1', 'ca-telegram');
    });
  });

  it('calls managed reconnect endpoint for managed account', async () => {
    const user = userEvent.setup();
    renderCard({ account: makeManagedAccount() });

    await user.click(screen.getByRole('button', { name: 'Reconnect' }));

    await waitFor(() => {
      expect(mocks.reconnectTelegramManagedBot).toHaveBeenCalledWith('s1', 'ca-telegram');
    });
  });
});
