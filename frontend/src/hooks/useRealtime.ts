import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { useShop } from '../contexts/ShopContext';
import { queryKeys } from '../lib/queryClient';
import { RealtimeClient } from '../services/realtimeClient';

/**
 * Subscribes to shop realtime events and invalidates affected React Query
 * caches so inbox, handoffs, and dashboard stay fresh without waiting for the
 * polling interval. Safe no-op when WebSocket/Redis is unavailable.
 */
export function useRealtime(): void {
  const { selectedShopId } = useShop();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!selectedShopId) {
      return undefined;
    }

    const client = new RealtimeClient(selectedShopId);
    client.connect();

    const unsubscribe = client.subscribe((event) => {
      switch (event.type) {
        case 'message.created':
        case 'conversation.updated': {
          queryClient.invalidateQueries({ queryKey: ['shops', selectedShopId, 'conversations'] });
          queryClient.invalidateQueries({ queryKey: queryKeys.handoffQueue(selectedShopId) });
          queryClient.invalidateQueries({ queryKey: ['shell-badge', 'handoffs', selectedShopId] });
          const conversationId = event.payload?.conversation_id;
          if (typeof conversationId === 'string') {
            queryClient.invalidateQueries({
              queryKey: queryKeys.conversation(selectedShopId, conversationId),
            });
          }
          break;
        }
        case 'order.updated': {
          queryClient.invalidateQueries({ queryKey: ['shops', selectedShopId, 'orders'] });
          break;
        }
        case 'job.failed': {
          queryClient.invalidateQueries({ queryKey: ['shell-badge', 'failed-jobs', selectedShopId] });
          break;
        }
        case 'metrics.tick': {
          queryClient.invalidateQueries({ queryKey: queryKeys.dashboardMetrics(selectedShopId) });
          break;
        }
        default:
          break;
      }
    });

    return () => {
      unsubscribe();
      client.close();
    };
  }, [selectedShopId, queryClient]);
}
