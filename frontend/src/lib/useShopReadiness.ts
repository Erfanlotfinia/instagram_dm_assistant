import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { apiClient } from '../services/apiClient';
import {
  evaluateCatalogCompleteness,
  evaluateChannelOnboarding,
  evaluateShopReadiness,
} from './readiness';
import type { AttributeAlias } from '../types/fashion';
import type { InstagramProductMap } from '../types/product';
import type { ChannelAccount } from '../types/channel';
import type {
  CatalogCompletenessScore,
  ChannelOnboardingState,
  ShopReadinessScore,
} from '../types/sprint2Readiness';

export interface ShopReadinessResult {
  data: {
    channelStates: ChannelOnboardingState[];
    catalogScore: CatalogCompletenessScore;
    shopReadiness: ShopReadinessScore;
  } | null;
  isLoading: boolean;
  error: unknown;
  /** Per-provider channel onboarding states (one per existing channel account). */
  channelStates: ChannelOnboardingState[];
  catalogScore: CatalogCompletenessScore | null;
  shopReadiness: ShopReadinessScore | null;
}

/**
 * Shared readiness data hook. Pulls everything from existing apiClient
 * endpoints and memoizes into the Sprint 2 readiness structures. Used by
 * ShopReadinessPanel and PilotChecklistPanel so readiness is computed in
 * exactly one place.
 *
 * Each query is enabled only when `shopId` is present and fails open: a
 * failed query does not throw for the whole hook — the missing input is
 * treated as "unknown" so Sprint 3 callers can degrade gracefully.
 */
export function useShopReadiness(shopId: string | null | undefined): ShopReadinessResult {
  const enabled = Boolean(shopId);

  const channelsQuery = useQuery({
    queryKey: ['channel-accounts', shopId],
    queryFn: () => apiClient.listChannelAccounts(shopId!),
    enabled,
  });
  const productsQuery = useQuery({
    queryKey: ['products', shopId],
    queryFn: () => apiClient.listProducts(shopId!),
    enabled,
  });
  const aliasesQuery = useQuery({
    queryKey: ['attribute-aliases', shopId],
    queryFn: () => apiClient.listAttributeAliases(shopId!),
    enabled,
  });
  const mappingsQuery = useQuery({
    queryKey: ['instagram-product-maps', shopId],
    queryFn: () => apiClient.listInstagramProductMaps(shopId!),
    enabled,
  });
  const pilotReadinessQuery = useQuery({
    queryKey: ['pilot-readiness', shopId],
    queryFn: () => apiClient.getPilotReadiness(shopId!),
    enabled,
  });
  const pilotSettingsQuery = useQuery({
    queryKey: ['pilot-settings', shopId],
    queryFn: () => apiClient.getPilotSettings(shopId!),
    enabled,
  });
  const riskQuery = useQuery({
    queryKey: ['agent-risk-settings', shopId],
    queryFn: () => apiClient.getAgentRiskSettings(shopId!),
    enabled,
  });
  const replayRunsQuery = useQuery({
    queryKey: ['replay-runs', shopId],
    queryFn: () => apiClient.listReplayRuns(shopId!),
    enabled,
  });
  const failedJobsQuery = useQuery({
    queryKey: ['failed-jobs', shopId, 'active'],
    queryFn: () => apiClient.listFailedJobs(shopId!, { status: 'failed', page: 1 }),
    enabled,
  });

  const queries = [
    channelsQuery,
    productsQuery,
    aliasesQuery,
    mappingsQuery,
    pilotReadinessQuery,
    pilotSettingsQuery,
    riskQuery,
    replayRunsQuery,
    failedJobsQuery,
  ];
  const isLoading = queries.some((q) => q.isLoading);
  const firstError = queries.find((q) => q.error)?.error ?? null;

  const memo = useMemo(() => {
    if (!shopId) return null;

    const channels: ChannelAccount[] = channelsQuery.data ?? [];
    const channelStates = channels.map((channel) => evaluateChannelOnboarding({ channel }));

    const catalogScore = evaluateCatalogCompleteness({
      products: productsQuery.data ?? [],
      attributeAliases: (aliasesQuery.data as AttributeAlias[] | undefined) ?? null,
      productMappings: (mappingsQuery.data as InstagramProductMap[] | undefined) ?? null,
    });

    const shopReadiness = evaluateShopReadiness({
      channelStates,
      catalog: catalogScore,
      pilotReadiness: pilotReadinessQuery.data ?? null,
      pilotSettings: pilotSettingsQuery.data ?? null,
      riskSettings: riskQuery.data ?? null,
      latestRun: replayRunsQuery.data?.[0] ?? null,
      failedJobsCount: failedJobsQuery.data?.total ?? 0,
    });

    return { channelStates, catalogScore, shopReadiness };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    shopId,
    channelsQuery.data,
    productsQuery.data,
    aliasesQuery.data,
    mappingsQuery.data,
    pilotReadinessQuery.data,
    pilotSettingsQuery.data,
    riskQuery.data,
    replayRunsQuery.data,
    failedJobsQuery.data,
  ]);

  return {
    data: memo,
    isLoading,
    error: firstError,
    channelStates: memo?.channelStates ?? [],
    catalogScore: memo?.catalogScore ?? null,
    shopReadiness: memo?.shopReadiness ?? null,
  };
}
