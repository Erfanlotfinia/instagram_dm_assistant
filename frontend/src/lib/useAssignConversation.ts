import { useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '../services/apiClient';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from './queryClient';

/**
 * Sprint 5 — shared assignment mutation used by the operator queue and the
 * operator conversation panel. Performs the existing `POST /conversations/{id}/assign`
 * call, invalidates queue + conversation queries, and surfaces a toast.
 *
 * Role gating is enforced by callers (operators can assign to self only;
 * admins/owners can assign to any shop member) — the backend enforces its own
 * permission rules as well.
 */
export interface UseAssignConversationOptions {
  shopId: string;
  conversationId: string;
}

export interface UseAssignConversationResult {
  assign: (operatorId: string) => void;
  isPending: boolean;
  error: unknown;
}

export function useAssignConversation({
  shopId,
  conversationId,
}: UseAssignConversationOptions): UseAssignConversationResult {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const mutation = useMutation({
    mutationFn: (operatorId: string) =>
      apiClient.assignConversation(shopId, conversationId, operatorId),
    onSuccess: (data) => {
      showToast(
        data.assigned_operator_name
          ? `Assigned to ${data.assigned_operator_name}.`
          : 'Conversation assigned.',
        'success',
      );
      void queryClient.invalidateQueries({ queryKey: queryKeys.conversation(shopId, conversationId) });
      void queryClient.invalidateQueries({ queryKey: ['shops', shopId, 'conversations'] });
      void queryClient.invalidateQueries({ queryKey: ['operator-workspace', shopId] });
      void queryClient.invalidateQueries({ queryKey: queryKeys.handoffQueue(shopId) });
    },
    onError: (err) => {
      showToast(err instanceof Error ? err.message : 'Assignment failed.', 'error');
    },
  });

  const assign = useCallback(
    (operatorId: string) => {
      mutation.mutate(operatorId);
    },
    [mutation],
  );

  return { assign, isPending: mutation.isPending, error: mutation.error };
}
