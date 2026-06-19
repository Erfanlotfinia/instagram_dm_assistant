import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { AttributeDictionaryPage } from './AttributeDictionaryPage';

vi.mock('../contexts/ShopContext', () => ({ useShop: () => ({ selectedShop: { id: 'shop-1', name: 'Demo' } }) }));
vi.mock('../contexts/ToastContext', () => ({ useToast: () => ({ showToast: vi.fn() }) }));
vi.mock('../services/apiClient', () => ({
  apiClient: {
    listAttributeAliases: vi.fn().mockResolvedValue([]),
    createAttributeAlias: vi.fn(),
  },
}));

describe('AttributeDictionaryPage', () => {
  it('renders the generic dictionary and industry-neutral examples', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter><AttributeDictionaryPage /></MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole('heading', { name: 'Attribute dictionary' })).toBeInTheDocument();
    expect(screen.getByText('storage: ۱۲۸ گیگ → 128GB')).toBeInTheDocument();
    expect(screen.getByText('warranty: گارانتی دار → with_warranty')).toBeInTheDocument();
    expect(screen.queryByText(/Legacy Dictionary/i)).not.toBeInTheDocument();
  });
});
