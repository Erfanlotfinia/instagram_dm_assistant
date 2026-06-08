import { useEffect, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { z } from 'zod';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { useAuth } from '../contexts/AuthContext';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { CustomerUpdate } from '../types/conversation';

const messageSchema = z.object({
  text: z.string().min(1, 'Message is required').max(4000),
});

const customerSchema = z.object({
  full_name: z.string().optional(),
  phone: z.string().optional(),
  city: z.string().optional(),
  address: z.string().optional(),
  postal_code: z.string().optional(),
  notes: z.string().optional(),
});

type MessageFormValues = z.infer<typeof messageSchema>;
type CustomerFormValues = z.infer<typeof customerSchema>;

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
  const [editedSuggestedText, setEditedSuggestedText] = useState('');

  const conversationQuery = useQuery({
    queryKey: queryKeys.conversation(shopId, conversationId ?? ''),
    queryFn: () => apiClient.getConversation(shopId, conversationId!),
    enabled: Boolean(shopId && conversationId),
  });

  const conversation = conversationQuery.data;
  const isAdmin = user?.role === 'owner' || user?.role === 'admin';

  const messageForm = useForm<MessageFormValues>({
    resolver: zodResolver(messageSchema),
    defaultValues: { text: '' },
  });

  const customerForm = useForm<CustomerFormValues>({
    resolver: zodResolver(customerSchema),
    values: {
      full_name: conversation?.customer?.full_name ?? '',
      phone: conversation?.customer?.phone ?? '',
      city: conversation?.customer?.city ?? '',
      address: conversation?.customer?.address ?? '',
      postal_code: conversation?.customer?.postal_code ?? '',
      notes: conversation?.customer?.notes ?? '',
    },
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

  const approveSuggestedMutation = useMutation({
    mutationFn: (replyId: string) => apiClient.approveSuggestedReply(shopId, replyId),
    onSuccess: () => { showToast('Suggested reply approved and sent.', 'success'); invalidateConversation(); },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Approve failed', 'error'),
  });

  const editSuggestedMutation = useMutation({
    mutationFn: ({ replyId, text }: { replyId: string; text: string }) => apiClient.editAndSendSuggestedReply(shopId, replyId, text),
    onSuccess: () => { showToast('Edited reply sent.', 'success'); setEditedSuggestedText(''); invalidateConversation(); },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Edit and send failed', 'error'),
  });

  const rejectSuggestedMutation = useMutation({
    mutationFn: (replyId: string) => apiClient.rejectSuggestedReply(shopId, replyId, 'Rejected by operator'),
    onSuccess: () => { showToast('Suggested reply rejected.', 'success'); invalidateConversation(); },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Reject failed', 'error'),
  });

  const pendingSuggestedReply = conversation?.suggested_replies?.[0];

  useEffect(() => {
    if (conversation) {
      setEditedSuggestedText(pendingSuggestedReply?.suggested_text ?? conversation.suggested_outbound ?? '');
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
    return <p className="loading-state">Loading conversation...</p>;
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

  const latestRun = conversation.agent_runs?.[0];
  const confidence = conversation.slots?.confidence ?? latestRun?.output_json?.confidence;
  const suggestedText = editedSuggestedText;

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Conversation</p>
        <h1>
          {conversation.customer?.full_name ??
            conversation.customer?.instagram_user_id ??
            conversation.customer_id}
        </h1>
        <p>
          Lifecycle: <strong>{conversation.state}</strong> · Workflow:{' '}
          <strong>{conversation.workflow_state}</strong> · Handoff:{' '}
          <strong>{conversation.handoff_required ? 'required' : 'none'}</strong>
        </p>
        {conversation.handoff_reason ? (
          <p>
            Handoff reason: <strong>{conversation.handoff_reason}</strong>
          </p>
        ) : null}

        <div className="detail-grid">
          <p>
            Linked product:{' '}
            {conversation.linked_product ? (
              <Link className="table-link" to={`/products/${conversation.linked_product.id}`}>
                {conversation.linked_product.title}
              </Link>
            ) : (
              '—'
            )}
          </p>
          <p>
            Linked order:{' '}
            {conversation.linked_order ? (
              <Link
                className="table-link"
                to={`/orders/${conversation.linked_order.id}?shopId=${shopId}`}
              >
                {conversation.linked_order.id.slice(0, 8)} · {conversation.linked_order.status}
              </Link>
            ) : (
              '—'
            )}
          </p>
        </div>

        {conversation.preview_required ? (
          <div className="empty-state">
            <strong>Suggested reply requires approval:</strong> {conversation.preview_reason ?? 'preview required'}
            <p>{conversation.suggested_outbound}</p>
          </div>
        ) : null}

        <div className="button-row">
          <button
            className="button button--primary"
            type="button"
            onClick={() => takeOverMutation.mutate()}
            disabled={takeOverMutation.isPending}
          >
            Take over
          </button>
          <button
            className="button button--ghost-dark"
            type="button"
            onClick={() => releaseMutation.mutate()}
            disabled={releaseMutation.isPending}
          >
            Release to agent
          </button>
          <button
            className="button button--ghost-dark"
            type="button"
            onClick={() => setShowResolveConfirm(true)}
          >
            Mark resolved
          </button>
          <button
            className="button button--ghost-dark"
            type="button"
            onClick={() => createOrderMutation.mutate()}
            disabled={createOrderMutation.isPending}
          >
            Create order
          </button>
        </div>

        <Link className="table-link" to="/conversations">
          Back to conversations
        </Link>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Send manual message</h2>
        <form
          className="inline-form"
          onSubmit={messageForm.handleSubmit((values) => sendMessageMutation.mutate(values))}
        >
          <label className="form-field">
            <span>Message</span>
            <textarea rows={3} {...messageForm.register('text')} />
            {messageForm.formState.errors.text ? (
              <span className="field-error">{messageForm.formState.errors.text.message}</span>
            ) : null}
          </label>
          <button className="button button--primary" type="submit" disabled={sendMessageMutation.isPending}>
            {sendMessageMutation.isPending ? 'Sending...' : 'Send message'}
          </button>
        </form>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Customer details</h2>
        <form
          className="inline-form"
          onSubmit={customerForm.handleSubmit((values) => updateCustomerMutation.mutate(values))}
        >
          <div className="filter-grid">
            <label className="form-field">
              <span>Full name</span>
              <input {...customerForm.register('full_name')} />
            </label>
            <label className="form-field">
              <span>Phone</span>
              <input {...customerForm.register('phone')} />
            </label>
            <label className="form-field">
              <span>City</span>
              <input {...customerForm.register('city')} />
            </label>
            <label className="form-field">
              <span>Postal code</span>
              <input {...customerForm.register('postal_code')} />
            </label>
          </div>
          <label className="form-field">
            <span>Address</span>
            <textarea rows={2} {...customerForm.register('address')} />
          </label>
          <label className="form-field">
            <span>Notes</span>
            <textarea rows={2} {...customerForm.register('notes')} />
          </label>
          <button
            className="button button--primary"
            type="submit"
            disabled={updateCustomerMutation.isPending}
          >
            Save customer
          </button>
        </form>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Extracted slots</h2>
        {conversation.slots ? (
          <div className="detail-grid">
            <p>Product: {conversation.slots.product_id ?? '—'}</p>
            <p>Variant: {conversation.slots.product_variant_id ?? '—'}</p>
            <p>Selected variant alternatives: {conversation.slots.variant_alternatives?.length ?? 0}</p>
            <p>
              Color / Size / Qty: {conversation.slots.color ?? '—'} ({conversation.slots.normalized_color ?? '—'}) / {conversation.slots.size ?? '—'} ({conversation.slots.normalized_size ?? '—'}){' '}
              / {conversation.slots.quantity ?? '—'}
            </p>
            <p>Missing: {conversation.slots.missing_fields.join(', ') || 'none'}</p>
          </div>
        ) : (
          <p className="empty-state">No extracted slots yet.</p>
        )}
        {confidence ? (
          <p>
            Confidence — intent: {String((confidence as Record<string, unknown>).intent ?? '—')} · slots:{' '}
            {String((confidence as Record<string, unknown>).slots ?? '—')} · product:{' '}
            {String((confidence as Record<string, unknown>).product ?? '—')}
          </p>
        ) : null}
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Suggested reply card</h2>
        {pendingSuggestedReply ? (
          <div className="empty-state" aria-label="Suggested reply card">
            <p><strong>Reason:</strong> {pendingSuggestedReply.reason ?? conversation.preview_reason ?? 'Preview required'}</p>
            <p>{pendingSuggestedReply.suggested_text}</p>
            <label className="form-field">
              <span>Edit before sending</span>
              <textarea rows={4} value={suggestedText} onChange={(event) => setEditedSuggestedText(event.target.value)} />
            </label>
            <div className="button-row">
              <button className="button button--primary" type="button" onClick={() => approveSuggestedMutation.mutate(pendingSuggestedReply.id)} disabled={approveSuggestedMutation.isPending}>Approve and send</button>
              <button className="button button--ghost-dark" type="button" onClick={() => editSuggestedMutation.mutate({ replyId: pendingSuggestedReply.id, text: suggestedText })} disabled={!suggestedText || editSuggestedMutation.isPending}>Edit and send</button>
              <button className="button button--danger" type="button" onClick={() => rejectSuggestedMutation.mutate(pendingSuggestedReply.id)} disabled={rejectSuggestedMutation.isPending}>Reject</button>
            </div>
          </div>
        ) : (
          <p className="empty-state">No pending suggested reply.</p>
        )}
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Full audit trail</h2>
        <ul className="simple-list">
          {(conversation.agent_actions ?? []).map((action) => (
            <li key={action.id}>
              <strong>{action.action_name}</strong> · {action.status} ·{' '}
              {new Date(action.created_at).toLocaleString()}
            </li>
          ))}
        </ul>
        {(conversation.agent_actions ?? []).length === 0 ? (
          <p className="empty-state">No agent actions logged yet.</p>
        ) : null}
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Message timeline</h2>
        <div className="message-thread">
          {conversation.messages.map((message) => (
            <article
              key={message.id}
              className={`message-bubble message-bubble--${message.direction}`}
            >
              <p className="message-bubble__meta">
                {message.direction} · {message.message_type} ·{' '}
                {new Date(message.created_at).toLocaleString()}
              </p>
              <p className="message-bubble__text">{message.text ?? '(no text)'}</p>
              {isAdmin && message.raw_payload ? (
                <details className="message-bubble__debug">
                  <summary>Raw payload</summary>
                  <pre>{JSON.stringify(message.raw_payload, null, 2)}</pre>
                </details>
              ) : null}
            </article>
          ))}
          {conversation.messages.length === 0 ? (
            <p className="empty-state">No messages in this conversation.</p>
          ) : null}
        </div>
      </section>

      <ConfirmDialog
        open={showResolveConfirm}
        title="Mark conversation resolved?"
        message="This closes the conversation and clears handoff state."
        confirmLabel="Mark resolved"
        onConfirm={() => resolveMutation.mutate()}
        onCancel={() => setShowResolveConfirm(false)}
        isLoading={resolveMutation.isPending}
      />
    </div>
  );
}
