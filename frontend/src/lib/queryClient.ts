import { QueryClient } from '@tanstack/react-query';

import type { ConversationListFilters } from '../types/conversation';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const queryKeys = {
  shops: ['shops'] as const,
  shop: (shopId: string) => ['shops', shopId] as const,
  shopSettings: (shopId: string) => ['shops', shopId, 'settings'] as const,
  dashboardMetrics: (shopId: string) => ['shops', shopId, 'dashboard'] as const,
  conversations: (shopId: string, filters?: ConversationListFilters) =>
    ['shops', shopId, 'conversations', filters ?? {}] as const,
  conversation: (shopId: string, conversationId: string) =>
    ['shops', shopId, 'conversations', conversationId] as const,
  products: (shopId: string) => ['shops', shopId, 'products'] as const,
  product: (shopId: string, productId: string) => ['shops', shopId, 'products', productId] as const,
  orders: (shopId: string, filters?: Record<string, unknown>) =>
    ['shops', shopId, 'orders', filters ?? {}] as const,
  order: (shopId: string, orderId: string) => ['shops', shopId, 'orders', orderId] as const,
  instagramMaps: (shopId: string) => ['shops', shopId, 'instagram-maps'] as const,
  shopMembers: (shopId: string) => ['shops', shopId, 'members'] as const,
};
