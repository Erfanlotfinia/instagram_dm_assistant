import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { AutomationStatusBadge } from '../components/inbox/AutomationStatusBadge';
import { ChannelBadge } from '../components/inbox/ChannelBadge';
import { MessageThread } from '../components/conversations/MessageThread';
import { SuggestedReplyPanel } from '../components/conversations/SuggestedReplyPanel';
import { Card, CardBody, CardHeader, Badge, Button } from '../components/ui';
import { PageHeader, LoadingState, ErrorState, EmptyState } from '../components/data';
import { Icons } from '../components/icons';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import { cn } from '../lib/cn';
import type { Conversation } from '../types/conversation';

function waitTime(iso: string | null): string {
  if (!iso) return '—';
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${mins}m waiting`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h waiting`;
  return `${Math.round(hours / 24)}d waiting`;
}

function priorityRank(conversation: Conversation): number {
  const order = { urgent: 0, high: 1, medium: 2, low: 3 } as const;
  return order[conversation.priority_level ?? 'low'];
}

function ContextPacket({ shopId, conversationId }: { shopId: string; conversationId: string }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [editedText, setEditedText] = useState('');

  const detailQuery = useQuery({
    queryKey: queryKeys.conversation(shopId, conversationId),
    queryFn: () => apiClient.getConversation(shopId, conversationId),
    enabled: Boolean(shopId && conversationId),
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: queryKeys.conversation(shopId, conversationId) });
    queryClient.invalidateQueries({ queryKey: queryKeys.handoffQueue(shopId) });
    queryClient.invalidateQueries({ queryKey: ['shops', shopId, 'conversations'] });
    queryClient.invalidateQueries({ queryKey: ['shell-badge', 'handoffs', shopId] });
  }

  const takeOver = useMutation({
    mutationFn: () => apiClient.takeOverConversation(shopId, conversationId),
    onSuccess: () => { showToast('You took over this conversation.', 'success'); invalidate(); },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Take over failed', 'error'),
  });
  const resolve = useMutation({
    mutationFn: () => apiClient.markConversationResolved(shopId, conversationId),
    onSuccess: () => { showToast('Conversation resolved.', 'success'); invalidate(); },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Resolve failed', 'error'),
  });
  const approveReply = useMutation({
    mutationFn: (replyId: string) => apiClient.approveSuggestedReply(shopId, replyId),
    onSuccess: () => { showToast('Reply approved and sent.', 'success'); invalidate(); },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Approve failed', 'error'),
  });
  const editReply = useMutation({
    mutationFn: ({ replyId, text }: { replyId: string; text: string }) =>
      apiClient.editAndSendSuggestedReply(shopId, replyId, text),
    onSuccess: () => { showToast('Edited reply sent.', 'success'); setEditedText(''); invalidate(); },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Edit failed', 'error'),
  });
  const rejectReply = useMutation({
    mutationFn: (replyId: string) => apiClient.rejectSuggestedReply(shopId, replyId, 'Rejected by operator'),
    onSuccess: () => { showToast('Reply rejected.', 'success'); invalidate(); },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Reject failed', 'error'),
  });

  if (detailQuery.isLoading) return <LoadingState label="Loading context packet…" />;
  if (detailQuery.error || !detailQuery.data) {
    return <ErrorState message={detailQuery.error instanceof Error ? detailQuery.error.message : 'Failed to load'} />;
  }

  const conversation = detailQuery.data;
  const customerName =
    conversation.customer?.full_name ?? conversation.customer?.instagram_user_id ?? conversation.customer_id.slice(0, 8);
  const lastMessages = conversation.messages.slice(-4);
  const pendingReply = conversation.suggested_replies?.find((reply) => reply.status === 'pending');
  const latestRisk = conversation.decision_trace_summary;

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader
          title={
            <span className="flex items-center gap-2">
              {customerName}
              <ChannelBadge channel={conversation.channel_provider} />
            </span>
          }
          description={conversation.handoff_reason ?? 'Escalated to a human operator'}
          actions={
            <Link to={`/inbox/${conversationId}?shopId=${shopId}`}>
              <Button variant="secondary" size="sm" leadingIcon={<Icons.inbox size={14} />}>Open</Button>
            </Link>
          }
        />
        <CardBody className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <div>
            <p className="text-xs text-subtle">Workflow</p>
            <p className="text-fg">{conversation.workflow_state.replace(/_/g, ' ')}</p>
          </div>
          <div>
            <p className="text-xs text-subtle">Product</p>
            <p className="truncate text-fg">{conversation.linked_product?.title ?? '—'}</p>
          </div>
          <div>
            <p className="text-xs text-subtle">Order</p>
            <p className="text-fg">{conversation.linked_order?.status ?? '—'}</p>
          </div>
          <div>
            <p className="text-xs text-subtle">Payment</p>
            <p className="text-fg">{conversation.linked_order?.payment_status ?? '—'}</p>
          </div>
          {latestRisk ? (
            <div className="col-span-2 sm:col-span-4">
              <p className="text-xs text-subtle">Decision summary</p>
              <p className="text-fg">{latestRisk}</p>
            </div>
          ) : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Recent messages" />
        <CardBody>
          <div className="max-h-72 overflow-y-auto">
            <MessageThread messages={lastMessages} />
          </div>
        </CardBody>
      </Card>

      {pendingReply ? (
        <Card>
          <CardHeader title="AI suggested reply" description="Review before sending to the customer." />
          <CardBody>
            <SuggestedReplyPanel
              reply={pendingReply}
              editedText={editedText}
              previewReason={conversation.preview_reason}
              onEdit={setEditedText}
              onApprove={() => approveReply.mutate(pendingReply.id)}
              onEditAndSend={() => editReply.mutate({ replyId: pendingReply.id, text: editedText })}
              onReject={() => rejectReply.mutate(pendingReply.id)}
              isApproving={approveReply.isPending}
              isEditing={editReply.isPending}
              isRejecting={rejectReply.isPending}
            />
          </CardBody>
        </Card>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button onClick={() => takeOver.mutate()} disabled={takeOver.isPending} leadingIcon={<Icons.user size={15} />}>
          Take over
        </Button>
        <Button variant="secondary" onClick={() => resolve.mutate()} disabled={resolve.isPending} leadingIcon={<Icons.check size={15} />}>
          Resolve
        </Button>
        <Link to={`/inbox/${conversationId}/intelligence?shopId=${shopId}`}>
          <Button variant="ghost" leadingIcon={<Icons.ai size={15} />}>Why this escalation?</Button>
        </Link>
      </div>
    </div>
  );
}

export function HandoffQueuePage() {
  const { selectedShopId } = useShop();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const queueQuery = useQuery({
    queryKey: queryKeys.handoffQueue(selectedShopId),
    queryFn: () => apiClient.listConversations(selectedShopId, { handoff_required: true }),
    enabled: Boolean(selectedShopId),
    refetchInterval: 15_000,
  });

  const queue = [...(queueQuery.data ?? [])].sort(
    (a, b) => priorityRank(a) - priorityRank(b) ||
      new Date(a.last_message_at ?? a.updated_at).getTime() - new Date(b.last_message_at ?? b.updated_at).getTime(),
  );

  useEffect(() => {
    if (!selectedId && queue.length > 0) {
      setSelectedId(queue[0].id);
    }
  }, [queue, selectedId]);

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow="Operations"
        title="Human Handoff Queue"
        description="Escalated conversations sorted by priority and wait time, with full context and AI suggestions."
        actions={<Badge tone={queue.length > 0 ? 'danger' : 'success'}>{queue.length} waiting</Badge>}
      />

      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        <Card className="h-fit">
          <CardHeader title="Queue" />
          <div className="max-h-[70vh] overflow-y-auto">
            {queueQuery.isLoading ? (
              <LoadingState />
            ) : queueQuery.error ? (
              <ErrorState message={queueQuery.error instanceof Error ? queueQuery.error.message : 'Failed to load'} />
            ) : queue.length === 0 ? (
              <EmptyState title="Queue is clear" description="No conversations are waiting for a human right now." />
            ) : (
              <ul>
                {queue.map((conversation) => {
                  const name =
                    conversation.customer?.full_name ?? conversation.customer?.instagram_user_id ?? conversation.customer_id.slice(0, 8);
                  return (
                    <li key={conversation.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedId(conversation.id)}
                        className={cn(
                          'w-full border-b border-border/70 px-4 py-3 text-left transition-colors hover:bg-surface-sunken',
                          conversation.id === selectedId && 'bg-accent-soft',
                        )}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="flex items-center gap-2 truncate">
                            <ChannelBadge channel={conversation.channel_provider} />
                            <span className="truncate text-sm font-medium text-fg">{name}</span>
                          </span>
                          {conversation.priority_level ? (
                            <Badge tone={conversation.priority_level === 'urgent' ? 'danger' : conversation.priority_level === 'high' ? 'warning' : 'neutral'}>
                              {conversation.priority_level}
                            </Badge>
                          ) : null}
                        </div>
                        <p className="mt-1 line-clamp-1 text-xs text-muted">
                          {conversation.handoff_reason ?? conversation.last_message_text ?? '—'}
                        </p>
                        <div className="mt-1.5 flex items-center justify-between">
                          <AutomationStatusBadge conversation={conversation} />
                          <span className="text-xs text-subtle">{waitTime(conversation.last_message_at)}</span>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </Card>

        <div>
          {selectedId ? (
            <ContextPacket shopId={selectedShopId} conversationId={selectedId} />
          ) : (
            <Card>
              <EmptyState title="Select an escalation" description="Choose a conversation to see its context packet." />
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
