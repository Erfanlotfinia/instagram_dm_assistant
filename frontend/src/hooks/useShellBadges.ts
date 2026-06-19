import { useQuery } from '@tanstack/react-query';

import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';

export interface ShellBadges {
  handoffs: number;
  failedJobs: number;
}

/** Lightweight counts used to badge the sidebar. Polls on a slow cadence. */
export function useShellBadges(): ShellBadges {
  const { selectedShopId } = useShop();

  const handoffQuery = useQuery({
    queryKey: ['shell-badge', 'handoffs', selectedShopId],
    queryFn: () => apiClient.listConversations(selectedShopId, { handoff_required: true }),
    enabled: Boolean(selectedShopId),
    refetchInterval: 60_000,
  });

  const jobsQuery = useQuery({
    queryKey: ['shell-badge', 'failed-jobs', selectedShopId],
    queryFn: () => apiClient.listFailedJobs(selectedShopId, { status: 'failed' }),
    enabled: Boolean(selectedShopId),
    refetchInterval: 60_000,
  });

  return {
    handoffs: handoffQuery.data?.length ?? 0,
    failedJobs: jobsQuery.data?.total ?? jobsQuery.data?.items?.length ?? 0,
  };
}
