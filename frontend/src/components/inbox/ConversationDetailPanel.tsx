import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';

import { AutomationStatusBadge } from './AutomationStatusBadge';
import { ChannelBadge } from './ChannelBadge';
import { ConversationContextPanel } from '../conversations/ConversationContextPanel';
import { DecisionTraceViewer } from '../conversations/DecisionTraceViewer';
import { MessageThread } from '../conversations/MessageThread';
import { SuggestedReplyPanel } from '../conversations/SuggestedReplyPanel';
import { Button } from '../ui';
import { Icons } from '../icons';
import { LoadingState, ErrorState } from '../data';
import { useShop } from '../../contexts/ShopContext';
import { useToast } from '../../contexts/ToastContext';
import { queryKeys } from '../../lib/queryClient';
import { apiClient } from '../../services/apiClient';
import { useInboxStore } from '../../stores/inboxStore';
import { cn } from '../../lib/cn';
import type { CustomerUpdate } from '../../types/conversation';

interface ConversationDetailPanelProps {
  conversationId: string;
}

export function ConversationDetailPanel({ conversationId }: ConversationDetailPanelProps) {
  const [searchParams] = useSearchParams();
  const { selectedShopId } = useShop();
  const shopId = searchParams.get('shopId') ?? selectedShopId;
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const { rightPanelTab, setRightPanelTab } = useInboxStore();
  const [draft, setDraft] = useState('');
  const [editedSuggestion, setEditedSuggestion] = useState('');

  const conversationQuery = useQuery({
    queryKey: queryKeys.conversation(shopId, conversationId),
    queryFn: () => apiClient.getConversation(shopId, conversationId),
    enabled: Boolean(shopId && conversationId),
    refetchInterval: 10_000,
  });

  const conversation = conversationQuery.data;

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: queryKeys.conversation(shopId, conversationId) });
    queryClient.invalidateQueries({ queryKey: ['shops', shopId, 'conversations'] });
  }

  const takeOver = useMutation({
    mutationFn: () => apiClient.takeOverConversation(shopId, conversationId),
    onSuccess: () => { showToast('You took over this conversation.', 'success'); invalidate(); },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Take over failed', 'error'),
  });
  const release = useMutation({
    mutationFn: () => apiClient.releaseConversationToAgent(shopId, conversationId),
    onSuccess: () => { showToast('Released back to the agent.', 'success'); invalidate(); },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Release failed', 'error'),
  });
  const sendMessage = useMutation({
    mutationFn: (text: string) => apiClient.sendConversationMessage(shopId, conversationId, { text }),
    onSuccess: () => { setDraft(''); invalidate(); },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Send failed', 'error'),
  });
  const resolve = useMutation({
    mutationFn: () => apiClient.markConversationResolved(shopId, conversationId),
    onSuccess: () => { showToast('Conversation resolved.', 'success'); invalidate(); },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Resolve failed', 'error'),
  });
  const saveCustomer = useMutation({
    mutationFn: (values: CustomerUpdate) => apiClient.updateConversationCustomer(shopId, conversationId, values),
    onSuccess: () => { showToast('Customer updated.', 'success'); invalidate(); },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Update failed', 'error'),
  });
  const approveReply = useMutation({
    mutationFn: (replyId: string) => apiClient.approveSuggestedReply(shopId, replyId),
    onSuccess: () => { showToast('Reply approved and sent.', 'success'); invalidate(); },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Approve failed', 'error'),
  });
  const editReply = useMutation({
    mutationFn: ({ replyId, text }: { replyId: string; text: string }) =>
      apiClient.editAndSendSuggestedReply(shopId, replyId, text),
    onSuccess: () => { showToast('Edited reply sent.', 'success'); setEditedSuggestion(''); invalidate(); },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Edit failed', 'error'),
  });
  const rejectReply = useMutation({
    mutationFn: (replyId: string) => apiClient.rejectSuggestedReply(shopId, replyId, 'Rejected by operator'),
    onSuccess: () => { showToast('Reply rejected.', 'success'); invalidate(); },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Reject failed', 'error'),
  });

  if (conversationQuery.isLoading) {
    return <LoadingState label="Loading conversation…" />;
  }
  if (conversationQuery.error || !conversation) {
    return <ErrorState message={conversationQuery.error instanceof Error ? conversationQuery.error.message : 'Failed to load conversation'} />;
  }

  const customerName =
    conversation.customer?.full_name ?? conversation.customer?.instagram_user_id ?? conversation.customer_id.slice(0, 8);
  const pendingReply = conversation.suggested_replies?.find((reply) => reply.status === 'pending');
  const isPaused = conversation.agent_paused;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-3">
        <Link to="/inbox" className="text-muted hover:text-fg lg:hidden" aria-label="Back to list">
          <Icons.chevronRight size={18} className="rotate-180" />
        </Link>
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent">
          {customerName.charAt(0).toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-fg">{customerName}</p>
          <div className="mt-0.5 flex items-center gap-2">
            <ChannelBadge channel={conversation.channel_provider} showLabel />
            {conversation.last_intent ? <span className="text-xs text-subtle">· {conversation.last_intent}</span> : null}
          </div>
        </div>
        <AutomationStatusBadge conversation={conversation} />
        <Link to={`/inbox/${conversationId}/intelligence?shopId=${shopId}`}>
          <Button variant="secondary" size="sm" leadingIcon={<Icons.ai size={14} />}>
            Why?
          </Button>
        </Link>
        {isPaused ? (
          <Button variant="secondary" size="sm" onClick={() => release.mutate()} disabled={release.isPending}>
            Release to agent
          </Button>
        ) : (
          <Button variant="secondary" size="sm" onClick={() => takeOver.mutate()} disabled={takeOver.isPending}>
            Take over
          </Button>
        )}
        <Button variant="ghost" size="sm" onClick={() => resolve.mutate()} disabled={resolve.isPending}>
          Resolve
        </Button>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[1fr_320px]">
        <div className="flex min-h-0 flex-col border-r border-border">
          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
            <MessageThread messages={conversation.messages} />
          </div>

          {pendingReply ? (
            <div className="border-t border-border px-4 py-3">
              <SuggestedReplyPanel
                reply={pendingReply}
                editedText={editedSuggestion}
                previewReason={conversation.preview_reason}
                onEdit={setEditedSuggestion}
                onApprove={() => approveReply.mutate(pendingReply.id)}
                onEditAndSend={() => editReply.mutate({ replyId: pendingReply.id, text: editedSuggestion })}
                onReject={() => rejectReply.mutate(pendingReply.id)}
                isApproving={approveReply.isPending}
                isEditing={editReply.isPending}
                isRejecting={rejectReply.isPending}
              />
            </div>
          ) : null}

          <form
            className="flex items-end gap-2 border-t border-border px-4 py-3"
            onSubmit={(event) => {
              event.preventDefault();
              if (draft.trim()) {
                sendMessage.mutate(draft.trim());
              }
            }}
          >
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
                  event.preventDefault();
                  if (draft.trim()) sendMessage.mutate(draft.trim());
                }
              }}
              rows={2}
              dir="auto"
              placeholder={isPaused ? 'Type a reply… (Ctrl+Enter to send)' : 'Take over to reply manually'}
              disabled={!isPaused || sendMessage.isPending}
              className={cn(
                'min-h-[44px] flex-1 resize-none rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg placeholder:text-subtle focus:border-accent focus:outline-none',
                !isPaused && 'opacity-60',
              )}
            />
            <Button type="submit" disabled={!isPaused || !draft.trim() || sendMessage.isPending}>
              Send
            </Button>
          </form>
        </div>

        <aside className="hidden min-h-0 flex-col overflow-y-auto lg:flex">
          <div className="flex gap-1 border-b border-border px-3 py-2" role="tablist">
            {(['trace', 'order', 'customer'] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={rightPanelTab === tab}
                onClick={() => setRightPanelTab(tab)}
                className={cn(
                  'flex-1 rounded-md px-2 py-1.5 text-xs font-medium capitalize',
                  rightPanelTab === tab ? 'bg-accent-soft text-accent' : 'text-muted hover:text-fg',
                )}
              >
                {tab === 'trace' ? 'AI trace' : tab}
              </button>
            ))}
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto p-3">
            {rightPanelTab === 'trace' ? (
              <DecisionTraceViewer shopId={shopId} conversationId={conversationId} />
            ) : (
              <ConversationContextPanel
                key={rightPanelTab}
                conversation={conversation}
                shopId={shopId}
                confidence={conversation.slots?.confidence}
                onSaveCustomer={(values) => saveCustomer.mutate(values)}
                isSavingCustomer={saveCustomer.isPending}
                defaultTab={rightPanelTab === 'order' ? 'order' : 'customer'}
              />
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
