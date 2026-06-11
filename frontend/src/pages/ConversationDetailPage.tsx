import { useEffect, useState, type KeyboardEvent } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { z } from 'zod';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { ConversationContextPanel } from '../components/conversations/ConversationContextPanel';
import { MessageThread } from '../components/conversations/MessageThread';
import { OperatorQuickActions } from '../components/conversations/OperatorQuickActions';
import { DecisionTraceViewer } from '../components/conversations/DecisionTraceViewer';
import { PriorityBadge } from '../components/conversations/PriorityBadge';
import { RiskBadge } from '../components/conversations/RiskBadge';
import { SuggestedReplyPanel } from '../components/conversations/SuggestedReplyPanel';
import { useAuth } from '../contexts/AuthContext';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { AgentWorkflowState, ConversationState, CustomerUpdate } from '../types/conversation';

const messageSchema = z.object({
  text: z.string().min(1, 'Message is required').max(4000),
});

type MessageFormValues = z.infer<typeof messageSchema>;

const STATE_LABELS: Record<ConversationState, string> = {
  open: 'Open',
  closed: 'Closed',
  pending_handoff: 'Pending handoff',
  archived: 'Archived',
};

const WORKFLOW_LABELS: Record<AgentWorkflowState, string> = {
  idle: 'Idle',
  waiting_for_product: 'Waiting for product',
  waiting_for_variant: 'Waiting for variant',
  waiting_for_customer_info: 'Waiting for customer info',
  waiting_for_confirmation: 'Waiting for confirmation',
  waiting_for_payment: 'Waiting for payment',
  paid: 'Paid',
  sent_to_shipping: 'Sent to shipping',
  completed: 'Completed',
  cancelled: 'Cancelled',
  human_handoff: 'Human handoff',
};

function customerDisplayName(conversation: {
  customer?: { full_name?: string | null; instagram_user_id?: string } | null;
  customer_id: string;
}): string {
  return (
    conversation.customer?.full_name ??
    conversation.customer?.instagram_user_id ??
    conversation.customer_id
  );
}

function customerInitial(name: string): string {
  return name.charAt(0).toUpperCase();
}

function formatActivityTime(iso: string | null | undefined): string | null {
  if (!iso) {
    return null;
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function ConversationDetailPage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const [searchParams] = useSearchParams();
  const { selectedShopId } = useShop();
  const shopId = searchParams.get('shopId') ?? selectedShopId;
  const { user } = useAuth();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [showResolveConfirm, setShowResolveConfirm] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [showTrackingPrompt, setShowTrackingPrompt] = useState(false);
  const [trackingCode, setTrackingCode] = useState('');
  const [editedSuggestedText, setEditedSuggestedText] = useState('');

  const conversationQuery = useQuery({
    queryKey: queryKeys.conversation(shopId, conversationId ?? ''),
    queryFn: () => apiClient.getConversation(shopId, conversationId!),
    enabled: Boolean(shopId && conversationId),
  });

  const conversation = conversationQuery.data;
  const tracesQuery = useQuery({
    queryKey: ['decision-traces', shopId, conversationId],
    queryFn: () => apiClient.listConversationDecisionTraces ? apiClient.listConversationDecisionTraces(shopId, conversationId!) : Promise.resolve([]),
    enabled: Boolean(shopId && conversationId),
  });
  const latestRisk = tracesQuery.data?.[0]?.risk_score;

  const messageForm = useForm<MessageFormValues>({
    resolver: zodResolver(messageSchema),
    defaultValues: { text: '' },
  });

  function invalidateConversation() {
    queryClient.invalidateQueries({ queryKey: queryKeys.conversation(shopId, conversationId!) });
    queryClient.invalidateQueries({ queryKey: queryKeys.conversations(shopId) });
  }

  const takeOverMutation = useMutation({
    mutationFn: () => apiClient.takeOverConversation(shopId, conversationId!),
    onSuccess: () => {
      showToast('You took over this conversation.', 'success');
      invalidateConversation();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Take over failed', 'error'),
  });

  const releaseMutation = useMutation({
    mutationFn: () => apiClient.releaseConversationToAgent(shopId, conversationId!),
    onSuccess: () => {
      showToast('Conversation released back to the agent.', 'success');
      invalidateConversation();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Release failed', 'error'),
  });

  const sendMessageMutation = useMutation({
    mutationFn: (values: MessageFormValues) =>
      apiClient.sendConversationMessage(shopId, conversationId!, values),
    onSuccess: () => {
      messageForm.reset();
      showToast('Message sent.', 'success');
      invalidateConversation();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Send failed', 'error'),
  });

  const resolveMutation = useMutation({
    mutationFn: () => apiClient.markConversationResolved(shopId, conversationId!),
    onSuccess: () => {
      setShowResolveConfirm(false);
      showToast('Conversation marked as resolved.', 'success');
      invalidateConversation();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Resolve failed', 'error'),
  });

  const updateCustomerMutation = useMutation({
    mutationFn: (values: CustomerUpdate) =>
      apiClient.updateConversationCustomer(shopId, conversationId!, values),
    onSuccess: () => {
      showToast('Customer details updated.', 'success');
      invalidateConversation();
    },
    onError: (error) =>
      showToast(error instanceof Error ? error.message : 'Customer update failed', 'error'),
  });

  const createOrderMutation = useMutation({
    mutationFn: () => apiClient.createOrderFromConversation(shopId, conversationId!),
    onSuccess: (order) => {
      showToast('Draft order created from conversation.', 'success');
      invalidateConversation();
      navigate(`/orders/${order.id}?shopId=${shopId}`);
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Order creation failed', 'error'),
  });

  const sendPaymentLinkMutation = useMutation({
    mutationFn: () => apiClient.sendPaymentLink(shopId, conversation!.linked_order!.id),
    onSuccess: () => {
      showToast('Payment link sent.', 'success');
      invalidateConversation();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Payment link failed', 'error'),
  });

  const markPaidMutation = useMutation({
    mutationFn: () => apiClient.markOrderPaid(shopId, conversation!.linked_order!.id),
    onSuccess: () => {
      showToast('Order marked as paid.', 'success');
      invalidateConversation();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Mark paid failed', 'error'),
  });

  const sendTrackingMutation = useMutation({
    mutationFn: (code: string) =>
      apiClient.sendTrackingCode(shopId, conversation!.linked_order!.id, {
        tracking_code: code,
      }),
    onSuccess: () => {
      setShowTrackingPrompt(false);
      setTrackingCode('');
      showToast('Tracking code sent.', 'success');
      invalidateConversation();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Tracking failed', 'error'),
  });

  const cancelOrderMutation = useMutation({
    mutationFn: () =>
      apiClient.cancelOrder(shopId, conversation!.linked_order!.id, {
        reason: 'Cancelled by operator',
      }),
    onSuccess: () => {
      setShowCancelConfirm(false);
      showToast('Order cancelled.', 'success');
      invalidateConversation();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Cancel failed', 'error'),
  });

  const approveSuggestedMutation = useMutation({
    mutationFn: (replyId: string) => apiClient.approveSuggestedReply(shopId, replyId),
    onSuccess: () => {
      showToast('Suggested reply approved and sent.', 'success');
      invalidateConversation();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Approve failed', 'error'),
  });

  const editSuggestedMutation = useMutation({
    mutationFn: ({ replyId, text }: { replyId: string; text: string }) =>
      apiClient.editAndSendSuggestedReply(shopId, replyId, text),
    onSuccess: () => {
      showToast('Edited reply sent.', 'success');
      setEditedSuggestedText('');
      invalidateConversation();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Edit and send failed', 'error'),
  });

  const rejectSuggestedMutation = useMutation({
    mutationFn: (replyId: string) => apiClient.rejectSuggestedReply(shopId, replyId, 'Rejected by operator'),
    onSuccess: () => {
      showToast('Suggested reply rejected.', 'success');
      invalidateConversation();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Reject failed', 'error'),
  });

  const messageText = messageForm.watch('text') ?? '';
  const trimmedMessage = messageText.trim();

  const submitMessage = messageForm.handleSubmit((values) => sendMessageMutation.mutate(values));

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, Shift+Enter inserts a newline. Ignore while composing (IME).
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      if (trimmedMessage && !sendMessageMutation.isPending) {
        void submitMessage();
      }
    }
  }

  const pendingSuggestedReply = conversation?.suggested_replies?.[0];
  const isMutating =
    takeOverMutation.isPending ||
    releaseMutation.isPending ||
    sendMessageMutation.isPending ||
    createOrderMutation.isPending ||
    sendPaymentLinkMutation.isPending ||
    markPaidMutation.isPending ||
    sendTrackingMutation.isPending ||
    cancelOrderMutation.isPending;

  useEffect(() => {
    if (conversation) {
      setEditedSuggestedText(
        pendingSuggestedReply?.suggested_text ?? conversation.suggested_outbound ?? '',
      );
    }
  }, [conversation, pendingSuggestedReply?.id, pendingSuggestedReply?.suggested_text]);

  if (!shopId) {
    return (
      <section className="dashboard-card">
        <p className="form-error">Select a shop to open this conversation.</p>
        <Link className="table-link" to="/conversations">
          Back to conversations
        </Link>
      </section>
    );
  }

  if (conversationQuery.isLoading) {
    return (
      <div className="conversation-workspace conversation-skeleton" aria-busy="true" aria-live="polite">
        <span className="visually-hidden">Loading conversation…</span>
        <div className="dashboard-card dashboard-card--wide conversation-skeleton__header">
          <div className="skeleton-line skeleton-line--avatar" />
          <div className="conversation-skeleton__header-text">
            <div className="skeleton-line skeleton-line--title" />
            <div className="skeleton-line skeleton-line--badges" />
          </div>
        </div>
        <div className="conversation-workspace__body">
          <section className="dashboard-card conversation-skeleton__chat">
            <div className="skeleton-bubble skeleton-bubble--inbound" />
            <div className="skeleton-bubble skeleton-bubble--outbound" />
            <div className="skeleton-bubble skeleton-bubble--inbound" />
            <div className="skeleton-line skeleton-line--composer" />
          </section>
          <div className="dashboard-card conversation-skeleton__panel">
            <div className="skeleton-line" />
            <div className="skeleton-line" />
            <div className="skeleton-line skeleton-line--short" />
          </div>
        </div>
      </div>
    );
  }

  if (conversationQuery.error || !conversation) {
    return (
      <section className="dashboard-card">
        <p className="form-error">
          {conversationQuery.error instanceof Error
            ? conversationQuery.error.message
            : 'Conversation not found'}
        </p>
        <Link className="table-link" to="/conversations">
          Back to conversations
        </Link>
      </section>
    );
  }

  const confidence =
    (conversation.slots?.confidence as Record<string, unknown> | undefined) ??
    (conversation.agent_runs?.[0]?.output_json?.confidence as Record<string, unknown> | undefined);

  const displayName = customerDisplayName(conversation);
  const stateLabel = STATE_LABELS[conversation.state] ?? conversation.state;
  const workflowLabel = WORKFLOW_LABELS[conversation.workflow_state] ?? conversation.workflow_state;
  const lastActivity = formatActivityTime(conversation.last_message_at ?? conversation.updated_at);
  const instagramHandle = conversation.customer?.instagram_user_id;

  return (
    <div className="conversation-workspace">
      <header className="conversation-workspace__header dashboard-card dashboard-card--wide">
        <div className="conversation-workspace__identity">
          <Link className="conversation-workspace__back" to="/conversations">
            ← Back to conversations
          </Link>

          <div className="conversation-workspace__profile">
            <div className="conversation-workspace__avatar" aria-hidden="true">
              {customerInitial(displayName)}
            </div>
            <div>
              <p className="dashboard-card__eyebrow">Conversation</p>
              <h1 className="conversation-workspace__title">{displayName}</h1>
              <div className="conversation-workspace__badges">
                <span className="status-pill status-pill--neutral">{stateLabel}</span>
                <span className="status-pill status-pill--neutral">{workflowLabel}</span>
                <PriorityBadge
                  level={conversation.priority_level}
                  score={conversation.priority_score}
                  reason={conversation.priority_reason}
                />
                <RiskBadge level={latestRisk?.risk_level} score={latestRisk?.score} />
                {conversation.handoff_required ? (
                  <span className="status-pill status-pill--warning">Handoff required</span>
                ) : null}
                {conversation.agent_paused ? (
                  <span className="status-pill status-pill--accent">Agent paused</span>
                ) : null}
              </div>

              <dl className="conversation-workspace__meta">
                {instagramHandle ? (
                  <div className="conversation-workspace__meta-item">
                    <dt>Instagram</dt>
                    <dd>@{instagramHandle}</dd>
                  </div>
                ) : null}
                <div className="conversation-workspace__meta-item">
                  <dt>Operator</dt>
                  <dd>{conversation.assigned_operator?.full_name ?? 'Unassigned'}</dd>
                </div>
                {lastActivity ? (
                  <div className="conversation-workspace__meta-item">
                    <dt>Last activity</dt>
                    <dd>
                      <time dateTime={conversation.last_message_at ?? conversation.updated_at}>
                        {lastActivity}
                      </time>
                    </dd>
                  </div>
                ) : null}
              </dl>
            </div>
          </div>
        </div>

        <OperatorQuickActions
          hasOrder={Boolean(conversation.linked_order)}
          orderStatus={conversation.linked_order?.status}
          paymentStatus={conversation.linked_order?.payment_status}
          onTakeOver={() => takeOverMutation.mutate()}
          onRelease={() => releaseMutation.mutate()}
          onResolve={() => setShowResolveConfirm(true)}
          onCreateOrder={() => createOrderMutation.mutate()}
          onSendPaymentLink={() => sendPaymentLinkMutation.mutate()}
          onMarkPaid={() => markPaidMutation.mutate()}
          onSendTracking={() => setShowTrackingPrompt(true)}
          onCancelOrder={() => setShowCancelConfirm(true)}
          isLoading={isMutating}
        />
      </header>

      <div className="conversation-workspace__body">
        <section className="conversation-chat dashboard-card">
          <h2 className="conversation-chat__title">Message timeline</h2>

          <div className="conversation-chat__thread">
            <MessageThread messages={conversation.messages} />
          </div>

          <SuggestedReplyPanel
            reply={pendingSuggestedReply}
            editedText={editedSuggestedText}
            previewReason={conversation.preview_reason}
            onEdit={setEditedSuggestedText}
            onApprove={() => approveSuggestedMutation.mutate(pendingSuggestedReply!.id)}
            onEditAndSend={() =>
              editSuggestedMutation.mutate({
                replyId: pendingSuggestedReply!.id,
                text: editedSuggestedText,
              })
            }
            onReject={() => rejectSuggestedMutation.mutate(pendingSuggestedReply!.id)}
            isApproving={approveSuggestedMutation.isPending}
            isEditing={editSuggestedMutation.isPending}
            isRejecting={rejectSuggestedMutation.isPending}
          />

          <form className="conversation-chat__composer" onSubmit={submitMessage}>
            <label className="form-field conversation-chat__compose-field">
              <span className="visually-hidden">Message</span>
              <textarea
                rows={3}
                maxLength={4000}
                placeholder="Write a manual reply to the customer…"
                dir="auto"
                {...messageForm.register('text')}
                onKeyDown={handleComposerKeyDown}
              />
              {messageForm.formState.errors.text ? (
                <span className="field-error">{messageForm.formState.errors.text.message}</span>
              ) : null}
            </label>
            <div className="conversation-chat__composer-footer">
              <p className="conversation-chat__composer-hint">
                <kbd>Enter</kbd> to send · <kbd>Shift</kbd>+<kbd>Enter</kbd> for a new line
                {messageText.length > 0 ? (
                  <span className="conversation-chat__composer-count">{messageText.length} / 4000</span>
                ) : null}
              </p>
              <button
                className="button button--primary"
                type="submit"
                disabled={!trimmedMessage || sendMessageMutation.isPending}
              >
                {sendMessageMutation.isPending ? 'Sending…' : 'Send message'}
              </button>
            </div>
          </form>
        </section>

        <div className="page-stack">
          <ConversationContextPanel
            conversation={conversation}
            shopId={shopId}
            confidence={confidence}
            onSaveCustomer={(values) => updateCustomerMutation.mutate(values)}
            isSavingCustomer={updateCustomerMutation.isPending}
          />
          <DecisionTraceViewer shopId={shopId} conversationId={conversation.id} />
        </div>
      </div>

      <ConfirmDialog
        open={showResolveConfirm}
        title="Mark conversation resolved?"
        message="This closes the conversation and clears handoff state."
        confirmLabel="Mark resolved"
        onConfirm={() => resolveMutation.mutate()}
        onCancel={() => setShowResolveConfirm(false)}
        isLoading={resolveMutation.isPending}
      />

      <ConfirmDialog
        open={showCancelConfirm}
        title="Cancel order?"
        message="This cancels the linked order for this conversation."
        confirmLabel="Cancel order"
        onConfirm={() => cancelOrderMutation.mutate()}
        onCancel={() => setShowCancelConfirm(false)}
        isLoading={cancelOrderMutation.isPending}
      />

      {showTrackingPrompt ? (
        <div className="dialog-overlay" role="presentation" onClick={() => setShowTrackingPrompt(false)}>
          <div className="dialog" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
            <h2>Send tracking code</h2>
            <label className="form-field">
              <span>Tracking code</span>
              <input value={trackingCode} onChange={(event) => setTrackingCode(event.target.value)} />
            </label>
            <div className="button-row">
              <button className="button button--ghost-dark" type="button" onClick={() => setShowTrackingPrompt(false)}>
                Cancel
              </button>
              <button
                className="button button--primary"
                type="button"
                disabled={!trackingCode || sendTrackingMutation.isPending}
                onClick={() => sendTrackingMutation.mutate(trackingCode)}
              >
                Send tracking
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
