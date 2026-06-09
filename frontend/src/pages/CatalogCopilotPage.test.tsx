import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';

import { queryClient } from '../lib/queryClient';
import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider } from '../contexts/ToastContext';
import { CatalogCopilotPage } from './CatalogCopilotPage';

vi.mock('../services/apiClient', () => ({
  apiClient: {
    listCatalogProducts: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 }),
    reindexCatalog: vi.fn(),
    resolveProduct: vi.fn(),
    resolveVariant: vi.fn(),
    getResolverTrace: vi.fn(),
    patchProductAliases: vi.fn(),
    submitResolverFeedback: vi.fn(),
  },
}));

describe('CatalogCopilotPage', () => {
  it('renders catalog copilot heading', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ShopProvider>
            <ToastProvider>
              <MemoryRouter>
                <CatalogCopilotPage />
              </MemoryRouter>
            </ToastProvider>
          </ShopProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );
    expect(screen.getByRole('heading', { name: 'Catalog Copilot' })).toBeInTheDocument();
  });
});
