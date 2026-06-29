import { useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { apiClient } from '../services/apiClient';
import { buildRevenueRecoveryDashboard } from './revenueRecovery';
import type { RevenueRecoveryAggregationInput, RevenueRecoveryDashboard } from '../types/sprint4Revenue';
import type { UnavailableDemandLog } from '../types/fashion';

export interface RevenueRecoveryResult {
  dashboard: RevenueRecoveryDashboard | null;
  isLoading: boolean;
  error: unknown;
  /** Partial-data warnings (e.g. a non-critical endpoint failed or data is incomplete). */
  warnings: string[];
  refetch: () => void;
}

/**
 * Sprint 4 — Revenue Recovery shared data hook.
 *
 * Aggregates everything the Revenue Recovery Center needs from existing
 * apiClient endpoints and memoizes it into a `RevenueRecoveryDashboard` via
 * the pure builders in `lib/revenueRecovery.ts`. Used by `RevenueRecoveryPage`
 * so recovery is computed in exactly one place.
 *
 * Design notes:
 * - No N+1 requests. Conversations and orders are fetched with server-side
 *   filters (`waiting_for_payment`, `ready_to_order`, `status=payment_pending`,
 *   `status=expired`) so we never pull the full unpaginated list.
 * - Each query is enabled only when `shopId` is present.
 * - Fail-open: a failed query appends a warning and continues; the dashboard
 *   is still computed from whichever data arrived. `error` is surfaced only
 *   when every primary query has failed.
 * - Gaps are documented inline. Notably, the orders list endpoint has no
 *   `recovery_status` filter and conversations/orders are unpaginated, so we
 *   rely on status filters to bound the result set.
 */
export function useRevenueRecovery(shopId: string | null | undefined): RevenueRecoveryResult {
  const enabled = Boolean(shopId);

  const lostDemandQuery = useQuery({
    queryKey: ['analytics-lost-demand', shopId],
    queryFn: () => apiClient.getAnalyticsLostDemand(shopId!, undefined, undefined, 1),
    enabled,
  });
  const unavailableDemandQuery = useQuery({
    queryKey: ['analytics-unavailable-demand', shopId],
    queryFn: () => apiClient.getAnalyticsUnavailableDemand(shopId!),
    enabled,
  });
  const stockDemandQuery = useQuery({
    queryKey: ['analytics-stock-demand', shopId],
    queryFn: () => apiClient.getAnalyticsStockDemand(shopId!),
    enabled,
  });
  const postRevenueQuery = useQuery({
    queryKey: ['post-revenue', shopId],
    queryFn: () => apiClient.getPostRevenueAnalytics(shopId!),
    enabled,
  });
  const postsQuery = useQuery({
    queryKey: ['analytics-posts', shopId],
    queryFn: () => apiClient.getAnalyticsPosts(shopId!),
    enabled,
  });
  const recoveryRulesQuery = useQuery({
    queryKey: ['recovery-rules', shopId],
    queryFn: () => apiClient.listRecoveryRules(shopId!),
    enabled,
  });
  const productsQuery = useQuery({
    queryKey: ['products', shopId],
    queryFn: () => apiClient.listProducts(shopId!),
    enabled,
  });
  // Server-filtered order slices — avoid pulling the full unpaginated orders list.
  const unpaidOrdersQuery = useQuery({
    queryKey: ['orders', shopId, 'payment_pending', 'unpaid'],
    queryFn: () => apiClient.listOrders(shopId!, { status: 'payment_pending', payment_status: 'unpaid' }),
    enabled,
  });
  const expiredOrdersQuery = useQuery({
    queryKey: ['orders', shopId, 'expired'],
    queryFn: () => apiClient.listOrders(shopId!, { status: 'expired' }),
    enabled,
  });
  // Server-filtered conversation slices.
  const waitingPaymentConversationsQuery = useQuery({
    queryKey: ['conversations', shopId, 'waiting_for_payment'],
    queryFn: () => apiClient.listConversations(shopId!, { waiting_for_payment: true }),
    enabled,
  });
  const readyToOrderConversationsQuery = useQuery({
    queryKey: ['conversations', shopId, 'ready_to_order'],
    queryFn: () => apiClient.listConversations(shopId!, { ready_to_order: true }),
    enabled,
  });
  // Raw unavailable demand logs — per-event rows carrying conversation/customer ids
  // for the restock waitlist. The backend log shape may or may not expose these
  // ids depending on version; we cast loosely and the builder skips rows without them.
  const demandLogsQuery = useQuery({
    queryKey: ['unavailable-demand-logs', shopId],
    queryFn: () => apiClient.listUnavailableDemand(shopId!),
    enabled,
  });

  const queries = [
    lostDemandQuery,
    unavailableDemandQuery,
    stockDemandQuery,
    postRevenueQuery,
    postsQuery,
    recoveryRulesQuery,
    productsQuery,
    unpaidOrdersQuery,
    expiredOrdersQuery,
    waitingPaymentConversationsQuery,
    readyToOrderConversationsQuery,
    demandLogsQuery,
  ];

  const isLoading = queries.some((q) => q.isLoading);
  const failedQueries = queries.filter((q) => q.isError);
  // Surface a hard error only when every primary query failed; otherwise treat
  // failures as partial-data warnings so the dashboard still renders.
  const allFailed = enabled && failedQueries.length === queries.length;
  const error = allFailed ? failedQueries[0]?.error ?? null : null;

  const warnings = useMemo(() => {
    const warns: string[] = [];
    if (!enabled) return warns;
    // Warn about bounded fetches / known gaps.
    warns.push(
      'Orders are fetched via status filters (payment_pending + expired) — abandoned orders in other terminal states may not appear.',
    );
    const failed = queries.filter((q) => q.isError);
    for (const q of failed) {
      const msg = q.error instanceof Error ? q.error.message : 'A recovery data source failed to load.';
      warns.push(msg);
    }
    if ((demandLogsQuery.data?.length ?? 0) > 0) {
      const withCustomer = (demandLogsQuery.data ?? []).filter(
        (log) => Boolean((log as UnavailableDemandLog & { conversation_id?: string }).conversation_id),
      ).length;
      if (withCustomer === 0) {
        warns.push('Unavailable demand logs do not expose conversation/customer ids — restock waitlist is empty.');
      }
    }
    return warns;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    enabled,
    lostDemandQuery.isError,
    unavailableDemandQuery.isError,
    stockDemandQuery.isError,
    postRevenueQuery.isError,
    postsQuery.isError,
    recoveryRulesQuery.isError,
    productsQuery.isError,
    unpaidOrdersQuery.isError,
    expiredOrdersQuery.isError,
    waitingPaymentConversationsQuery.isError,
    readyToOrderConversationsQuery.isError,
    demandLogsQuery.isError,
    demandLogsQuery.data,
  ]);

  const dashboard = useMemo<RevenueRecoveryDashboard | null>(() => {
    if (!shopId) return null;

    const orders = [
      ...(unpaidOrdersQuery.data ?? []),
      ...(expiredOrdersQuery.data ?? []),
    ];
    const conversations = [
      ...(waitingPaymentConversationsQuery.data ?? []),
      ...(readyToOrderConversationsQuery.data ?? []),
    ];

    const aggregationInput: RevenueRecoveryAggregationInput = {
      shopId,
      lostDemand: lostDemandQuery.data?.items ?? null,
      unavailableDemand: unavailableDemandQuery.data ?? null,
      stockDemand: stockDemandQuery.data ?? null,
      unavailableDemandLogs: demandLogsQuery.data as
        | RevenueRecoveryAggregationInput['unavailableDemandLogs']
        | undefined,
      orders,
      recoveryRules: recoveryRulesQuery.data ?? null,
      conversations,
      postRevenue: postRevenueQuery.data ?? null,
      postPerformance: postsQuery.data ?? null,
      products: productsQuery.data ?? null,
    };

    return buildRevenueRecoveryDashboard(aggregationInput);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    shopId,
    lostDemandQuery.data,
    unavailableDemandQuery.data,
    stockDemandQuery.data,
    demandLogsQuery.data,
    unpaidOrdersQuery.data,
    expiredOrdersQuery.data,
    waitingPaymentConversationsQuery.data,
    readyToOrderConversationsQuery.data,
    recoveryRulesQuery.data,
    postRevenueQuery.data,
    postsQuery.data,
    productsQuery.data,
  ]);

  const refetch = useCallback(() => {
    for (const q of queries) {
      void q.refetch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    lostDemandQuery.refetch,
    unavailableDemandQuery.refetch,
    stockDemandQuery.refetch,
    postRevenueQuery.refetch,
    postsQuery.refetch,
    recoveryRulesQuery.refetch,
    productsQuery.refetch,
    unpaidOrdersQuery.refetch,
    expiredOrdersQuery.refetch,
    waitingPaymentConversationsQuery.refetch,
    readyToOrderConversationsQuery.refetch,
    demandLogsQuery.refetch,
  ]);

  return { dashboard, isLoading, error, warnings, refetch };
}
