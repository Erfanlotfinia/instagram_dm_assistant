import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import { InstagramConnectCard } from './InstagramConnectCard';
import type { ChannelAccount } from '../../types/channel';

const mocks = vi.hoisted(() => ({
  startInstagramConnect: vi.fn(),
  reconnectInstagram: vi.fn(),
  disconnectChannel: vi.fn(),
}));

vi.mock('../../services/apiClient', () => ({
  apiClient: {
    startInstagramConnect: mocks.startInstagramConnect,
    reconnectInstagram: mocks.reconnectInstagram,
    disconnectChannel: mocks.disconnectChannel,
  },
}));

vi.mock('../../contexts/ToastContext', () => ({
  useToast: () => ({ showToast: vi.fn() }),
}));

const connectedAccount: ChannelAccount = {
  id: 'ig-1',
  shop_id: 's1',
  provider: 'instagram',
  display_name: '@demo_shop',
  external_account_id: 'ig-biz-1',
  status: 'connected',
  capabilities_json: { supports_text: true },
  settings_json: { instagram_username: 'demo_shop', page_name: 'Demo Page' },
  token_configured: true,
  bot_token_configured: false,
  webhook_secret_configured: true,
  webhook_verify_token_configured: true,
  last_validation_at: '2026-06-19T00:00:00Z',
  last_error: null,
  created_at: '2026-06-19T00:00:00Z',
  updated_at: '2026-06-19T00:00:00Z',
};

describe('InstagramConnectCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.startInstagramConnect.mockResolvedValue({
      authorization_url: 'https://www.facebook.com/oauth',
      session_id: 'session-1',
      expires_at: '2026-06-19T01:00:00Z',
    });
    Object.defineProperty(window, 'location', {
      value: { assign: vi.fn() },
      writable: true,
    });
  });

  it('shows connect button and Meta redirect copy when not connected', () => {
    render(<InstagramConnectCard shopId="s1" account={null} canManage onRefresh={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Connect Instagram' })).toBeInTheDocument();
    expect(screen.getByText(/never ask for your Instagram password/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/access token/i)).not.toBeInTheDocument();
  });

  it('redirects browser to authorization_url on connect', async () => {
    const user = userEvent.setup();
    render(<InstagramConnectCard shopId="s1" account={null} canManage onRefresh={vi.fn()} />);
    await user.click(screen.getByRole('button', { name: 'Connect Instagram' }));
    expect(mocks.startInstagramConnect).toHaveBeenCalledWith('s1');
    expect(window.location.assign).toHaveBeenCalledWith('https://www.facebook.com/oauth');
  });

  it('shows encrypted token status when connected', () => {
    render(
      <InstagramConnectCard shopId="s1" account={connectedAccount} canManage onRefresh={vi.fn()} />,
    );
    expect(screen.getByText('Encrypted')).toBeInTheDocument();
    expect(screen.getByText(/@demo_shop/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Disconnect' })).toBeInTheDocument();
  });
});
