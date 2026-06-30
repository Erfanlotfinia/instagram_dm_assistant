import { useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { apiClient } from '../services/apiClient';
import { useAuth } from '../contexts/AuthContext';
import {
  buildOperatorQueueItems,
  buildWorkspaceSummary,
  type QueueBuildInput,
} from './operatorWorkspace';
import type {
  AgentDecisionTrace,
  Conversation,
  CustomerProfile,
} from '../types/conversation';
import type { Order } from '../types/order';
import type {
  OperatorQueueItem,
  OperatorWorkspaceSummary,
} from '../types/sprint5Operator';
import type { OperatorPerformanceRow } from '../types/competitive';

export interface OperatorWorkspaceResult {
  summary: OperatorWorkspaceSummary;
  queueItems: OperatorQueueItem[];
  conversations: Conversation[];
  traces: AgentDecisionTrace[];
  operatorPerformance: OperatorPerformanceRow[];
  isLoading: boolean;
  error: unknown;
  /** Partial-data warnings (non-critical sources failed or unavailable). */
  warnings: string[];
  refetch: () => void;
}

/**
 * Sprint 5 — Operator workspace shared data hook.
 *
 * Aggregates everything the operator workspace needs from EXISTING apiClient
 * endpoints and memoizes the prioritized queue via the pure builders in
 * `operatorWorkspace.ts`. Used by `OperatorWorkspacePage`, the workload panel,
 * and the operator conversation panel so the queue is computed in one place.
 *
 * Design notes:
 * - No N+1. Uses list endpoints only; no per-conversation detail fetch on load.
 * - Each query is enabled only when `shopId` is present.
 * - Fail-open: a failed non-critical query appends a warning and continues.
 *   `error` is surfaced only when the primary conversations query fails.
 * - `listConversations` is unpaginated on the backend; we pull a single
 *   unfiltered slice and let the builders compute SLA + priority client-side.
 */
export function useOperatorWorkspace(shopId: string | null | undefined): OperatorWorkspaceResult {
  const { user } = useAuth();
  const enabled = Boolean(shopId);

  // Primary: the conversation list (queue source of truth).
  const conversationsQuery = useQuery({
    queryKey: ['operator-workspace', shopId, 'conversations'],
    queryFn: () => apiClient.listConversations(shopId!, {}),
    enabled,
    refetchInterval: 15_000,
  });

  // Decision traces (shop-wide) — bounded by backend ordering (newest first);
  // we cap to the first 100 to avoid unbounded memory on large shops.
  const tracesQuery = useQuery({
    queryKey: ['operator-workspace', shopId, 'traces'],
    queryFn: async () => {
      const all = await apiClient.listDecisionTraces(shopId!);
      return all.slice(0, 100);
    },
    enabled,
  });

  // Bounded order slices for revenue / unpaid-order context.
  const unpaidOrdersQuery = useQuery({
    queryKey: ['operator-workspace', shopId, 'orders', 'unpaid'],
    queryFn: () => apiClient.listOrders(shopId!, { payment_status: 'unpaid' }),
    enabled,
  });
  const pendingOrdersQuery = useQuery({
    queryKey: ['operator-workspace', shopId, 'orders', 'pending'],
    queryFn: () => apiClient.listOrders(shopId!, { payment_status: 'pending' }),
    enabled,
  });

  // Historical operator performance for the workload panel.
  const operatorPerformanceQuery = useQuery({
    queryKey: ['operator-workspace', shopId, 'operator-performance'],
    queryFn: () => apiClient.getAnalyticsOperatorPerformance(shopId!),
    enabled,
  });

  const primaryQueries = [conversationsQuery];
  const secondaryQueries = [tracesQuery, unpaidOrdersQuery, pendingOrdersQuery, operatorPerformanceQuery];

  const isLoading = [...primaryQueries, ...secondaryQueries].some((q) => q.isLoading);
  const primaryFailed = primaryQueries.some((q) => q.isError);
  const error = primaryFailed ? conversationsQuery.error : null;

  const warnings = useMemo(() => {
    const warns: string[] = [];
    if (!enabled) return warns;
    for (const q of secondaryQueries) {
      if (q.isError) {
        warns.push(q.error instanceof Error ? q.error.message : 'An operator data source failed to load.');
      }
    }
    if (!user) {
      warns.push('Current operator unknown — "assigned to me" counts may be incomplete.');
    }
    return warns;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    enabled,
    user,
    tracesQuery.isError,
    tracesQuery.error,
    unpaidOrdersQuery.isError,
    unpaidOrdersQuery.error,
    pendingOrdersQuery.isError,
    pendingOrdersQuery.error,
    operatorPerformanceQuery.isError,
    operatorPerformanceQuery.error,
  ]);

  const conversations = conversationsQuery.data ?? [];
  const traces = tracesQuery.data ?? [];
  const orders: Order[] = [
    ...(unpaidOrdersQuery.data ?? []),
    ...(pendingOrdersQuery.data ?? []),
  ];
  const operatorPerformance = operatorPerformanceQuery.data?.items ?? [];

  const customers: Record<string, CustomerProfile | null> = useMemo(() => {
    // Customer profile is not fetched in bulk here (no N+1). The conversation
    // list embeds a customer summary; full profile is loaded per-conversation
    // in the operator conversation panel. This map stays empty intentionally.
    return {};
  }, []);

  const queueItems = useMemo<OperatorQueueItem[]>(() => {
    const input: QueueBuildInput = {
      conversations,
      decisionTraces: traces,
      customers,
      orders,
      revenueOpportunities: orders.map((o) => ({
        conversation_id: o.conversation_id,
        label: `Unpaid order ${o.id.slice(0, 8)} · ${o.total_amount} ${o.currency}`,
      })),
      currentOperatorId: user?.id ?? null,
    };
    return buildOperatorQueueItems(input);
  }, [conversations, traces, customers, orders, user?.id]);

  const summary = useMemo(
    () => buildWorkspaceSummary(queueItems, user?.id ?? null),
    [queueItems, user?.id],
  );

  const refetch = useCallback(() => {
    void conversationsQuery.refetch();
    void tracesQuery.refetch();
    void unpaidOrdersQuery.refetch();
    void pendingOrdersQuery.refetch();
    void operatorPerformanceQuery.refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    conversationsQuery.refetch,
    tracesQuery.refetch,
    unpaidOrdersQuery.refetch,
    pendingOrdersQuery.refetch,
    operatorPerformanceQuery.refetch,
  ]);

  return {
    summary,
    queueItems,
    conversations,
    traces,
    operatorPerformance,
    isLoading,
    error,
    warnings,
    refetch,
  };
}
