import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { App } from './App';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    login: vi.fn(),
    getMe: vi.fn().mockRejectedValue(new Error('not authenticated')),
    listShops: vi.fn().mockResolvedValue([]),
  },
}));

describe('App', () => {
  it('renders the login page for unauthenticated users', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
    });
  });
});
