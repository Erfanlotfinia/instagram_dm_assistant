import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import { ProfilePage } from './ProfilePage';

const mockUser = {
  id: 'u1',
  email: 'admin@test.com',
  full_name: 'Test Admin',
  role: 'owner' as const,
  is_active: true,
};

const mocks = vi.hoisted(() => ({
  getMe: vi.fn(),
  updateMe: vi.fn(),
  changePassword: vi.fn(),
  listShops: vi.fn(),
}));

vi.mock('../services/apiClient', () => ({
  apiClient: {
    login: vi.fn(),
    getMe: mocks.getMe,
    updateMe: mocks.updateMe,
    changePassword: mocks.changePassword,
    listShops: mocks.listShops,
  },
}));

function renderProfilePage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthProvider>
          <ShopProvider>
            <ToastProvider>
              <ProfilePage />
            </ToastProvider>
          </ShopProvider>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProfilePage', () => {
  beforeEach(() => {
    mocks.getMe.mockResolvedValue(mockUser);
    mocks.updateMe.mockResolvedValue({ ...mockUser, full_name: 'Updated Admin' });
    mocks.changePassword.mockResolvedValue(undefined);
    mocks.listShops.mockResolvedValue([
      { id: 's1', name: 'Demo Shop', slug: 'demo-shop', status: 'active', default_currency: 'USD' },
    ]);
  });

  it('renders profile details and shop access', async () => {
    renderProfilePage();

    expect(await screen.findByRole('heading', { name: 'Profile' })).toBeInTheDocument();
    expect(screen.getByText('Test Admin')).toBeInTheDocument();
    expect(screen.getByText('admin@test.com')).toBeInTheDocument();
    expect(await screen.findByText('Demo Shop')).toBeInTheDocument();
  });

  it('updates display name', async () => {
    const user = userEvent.setup();
    renderProfilePage();

    const nameInput = await screen.findByLabelText('Display name');
    await user.clear(nameInput);
    await user.type(nameInput, 'Updated Admin');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));

    await waitFor(() => {
      expect(mocks.updateMe).toHaveBeenCalledWith({ full_name: 'Updated Admin' });
    });
    expect(screen.getAllByText('Updated Admin').length).toBeGreaterThan(0);
  });

  it('validates password confirmation', async () => {
    const user = userEvent.setup();
    renderProfilePage();

    await screen.findByLabelText('Display name');
    await user.type(screen.getByLabelText('Current password'), 'password123');
    await user.type(screen.getByLabelText('New password'), 'newpassword123');
    await user.type(screen.getByLabelText('Confirm new password'), 'different123');
    await user.click(screen.getByRole('button', { name: 'Update password' }));

    expect(await screen.findByText('Passwords do not match')).toBeInTheDocument();
    expect(mocks.changePassword).not.toHaveBeenCalled();
  });
});
