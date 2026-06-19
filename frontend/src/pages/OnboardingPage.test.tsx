import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { OnboardingPage } from './OnboardingPage';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    getMe: vi.fn().mockResolvedValue({ id: 'u1', email: 'a@test.com', full_name: 'Admin', role: 'owner' }),
    listShops: vi.fn().mockResolvedValue([{ id: 's1', name: 'Demo', slug: 'demo', status: 'active' }]),
    getOnboardingStatus: vi.fn().mockResolvedValue({
      shop_id: 's1',
      completed_steps: ['shop_profile'],
      missing_steps: ['connect_instagram', 'first_product'],
      progress_percent: 11,
      next_recommended_action: 'Connect an Instagram business account to receive DMs.',
      total_steps: 9,
      steps: [
        { key: 'shop_profile', label: 'Create shop profile', completed: true, href: '/shops' },
        { key: 'connect_instagram', label: 'Connect Instagram account', completed: false, href: '/system/channels' },
        { key: 'first_product', label: 'Add first product', completed: false, href: '/products' },
      ],
    }),
  },
}));

describe('OnboardingPage', () => {
  it('renders checklist, progress bar, and next recommended action', async () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <AuthProvider>
          <ShopProvider>
            <MemoryRouter>
              <OnboardingPage />
            </MemoryRouter>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    expect(await screen.findByText('1 of 9 steps complete')).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: 'Onboarding progress' })).toHaveAttribute('aria-valuenow', '11');
    expect(screen.getByText('Next recommended action')).toBeInTheDocument();
    expect(screen.getByText('Connect an Instagram business account to receive DMs.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Connect Instagram account' })).toHaveAttribute('href', '/system/channels');
    expect(screen.getByText('Create shop profile')).toBeInTheDocument();
  });
});
