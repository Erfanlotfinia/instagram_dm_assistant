import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Badge, Button, Card, CardBody, CardHeader, StatusBanner } from '../ui';
import { EmptyState, ErrorState, LoadingState } from '../data';
import { apiClient } from '../../services/apiClient';
import { queryKeys } from '../../lib/queryClient';
import { buildCustomerTimeline, deriveConversationSla } from '../../lib/operatorWorkspace';
import { AssignmentControls, SlaBadge } from './AssignmentControls';
import { CustomerTimeline } from './CustomerTimeline';
import { QuickReplyPanel } from './QuickReplyPanel';
import { SuggestedReplyPanel } from '../conversations/SuggestedReplyPanel';
import { useToast } from '../../contexts/ToastContext';
import type { CustomerTimelineItem } from '../../types/sprint5Operator';

interface OperatorConversationPanelProps {
  conversationId: string;
  shopId: string;
}

/**
 * Sprint 5 — operator context panel for a single conversation. Renders SLA,
 * assignment, priority reason, AI understanding, customer timeline, open
 * orders, suggested replies, and quick replies. Loaded additively inside the
 * existing conversation context panel as a new "Operator" tab.
 */
export function OperatorConversationPanel({ conversationId, shopId }: OperatorConversationPanelProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [editedText, setEditedText] = useState('');

  const detailQuery = useQuery({
    queryKey: queryKeys.conversation(shopId, conversationId),
    queryFn: () => apiClient.getConversation(shopId, conversationId),
    enabled: Boolean(shopId && conversationId),
  });

  const tracesQuery = useQuery({
    queryKey: queryKeys.conversationIntelligence(shopId, conversationId),
    queryFn: () => apiClient.listConversationDecisionTraces(shopId, conversationId),
    enabled: Boolean(shopId && conversationId),
  });

  const pendingReply = detailQuery.data?.suggested_replies?.find((r) => r.status === 'pending');

  const approveReply = useMutation({
    mutationFn: (replyId: string) => apiClient.approveSuggestedReply(shopId, replyId),
    onSuccess: () => {
      showToast('Reply approved and sent.', 'success');
      void queryClient.invalidateQueries({ queryKey: queryKeys.conversation(shopId, conversationId) });
    },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Approve failed', 'error'),
  });
  const editReply = useMutation({
    mutationFn: ({ replyId, text }: { replyId: string; text: string }) =>
      apiClient.editAndSendSuggestedReply(shopId, replyId, text),
    onSuccess: () => {
      showToast('Edited reply sent.', 'success');
      setEditedText('');
      void queryClient.invalidateQueries({ queryKey: queryKeys.conversation(shopId, conversationId) });
    },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Edit failed', 'error'),
  });
  const rejectReply = useMutation({
    mutationFn: (replyId: string) => apiClient.rejectSuggestedReply(shopId, replyId, 'Rejected by operator'),
    onSuccess: () => {
      showToast('Reply rejected.', 'success');
      void queryClient.invalidateQueries({ queryKey: queryKeys.conversation(shopId, conversationId) });
    },
    onError: (e) => showToast(e instanceof Error ? e.message : 'Reject failed', 'error'),
  });

  const timeline = useMemo<CustomerTimelineItem[]>(() => {
    const conv = detailQuery.data;
    if (!conv) return [];
    return buildCustomerTimeline({
      messages: conv.messages,
      events: conv.events,
      decisionTraces: tracesQuery.data,
      previousOrders: conv.customer_profile?.previous_orders,
      conversationId,
      shopId,
    });
  }, [detailQuery.data, tracesQuery.data, conversationId, shopId]);

  if (detailQuery.isLoading) {
    return <LoadingState label="Loading operator context…" />;
  }
  if (detailQuery.error || !detailQuery.data) {
    return (
      <ErrorState
        message={detailQuery.error instanceof Error ? detailQuery.error.message : 'Failed to load conversation.'}
      />
    );
  }

  const conversation = detailQuery.data;
  const traces = tracesQuery.data ?? [];
  const latestTrace = traces[0] ?? null;
  const { waitingMinutes, slaState, priority } = deriveConversationSla(conversation, traces);
  const customerName =
    conversation.customer?.full_name ??
    conversation.customer?.instagram_user_id ??
    conversation.customer_id.slice(0, 8);
  const productName = conversation.linked_product?.title ?? null;
  const orderId = conversation.linked_order?.id ?? null;
  const customerContext = {
    customer_name: customerName,
    product_name: productName,
    order_id: orderId,
    city: conversation.customer_profile?.city ?? conversation.customer?.city ?? null,
    channel_name: conversation.channel_provider ?? null,
  };

  const riskWarning =
    latestTrace?.risk_score?.risk_level === 'high' ||
    latestTrace?.risk_score?.risk_level === 'critical' ||
    latestTrace?.human_handoff_required === true ||
    latestTrace?.risk_score?.requires_preview === true;

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader title="SLA & priority" />
        <CardBody className="flex flex-wrap items-center gap-3">
          <SlaBadge state={slaState} waitingMinutes={waitingMinutes} />
          <Badge tone={priority === 'urgent' ? 'danger' : priority === 'high' ? 'warning' : 'neutral'}>
            Priority: {priority}
          </Badge>
          {conversation.priority_reason ? (
            <span className="text-xs text-muted">{conversation.priority_reason}</span>
          ) : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Assignment" />
        <CardBody>
          <AssignmentControls
            shopId={shopId}
            conversationId={conversationId}
            assignedOperatorId={conversation.assigned_operator_id}
            assignedOperatorName={conversation.assigned_operator?.full_name ?? null}
          />
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="AI understanding"
          actions={
            <Link to={`/inbox/${conversationId}/intelligence?shopId=${shopId}`}>
              <Button variant="ghost" size="sm">
                View reasoning
              </Button>
            </Link>
          }
        />
        <CardBody>
          {conversation.decision_trace_summary || latestTrace?.reasoning_summary ? (
            <p className="text-sm text-fg">
              {latestTrace?.reasoning_summary ?? conversation.decision_trace_summary}
            </p>
          ) : (
            <p className="text-sm text-muted">No agent decisions recorded yet.</p>
          )}
        </CardBody>
      </Card>

      {riskWarning ? (
        <StatusBanner
          tone="warning"
          title="High-risk context"
          description="Latest AI decision flagged high risk, preview requirement, or human handoff. Review carefully before sending."
        />
      ) : null}

      <Card>
        <CardHeader title="Customer timeline" />
        <CardBody>
          <CustomerTimeline items={timeline} />
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Open orders" />
        <CardBody>
          {conversation.linked_order ? (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm text-fg">#{conversation.linked_order.id.slice(0, 8)}</span>
                <Badge tone="neutral">{conversation.linked_order.status.replace(/_/g, ' ')}</Badge>
                <Badge tone={conversation.linked_order.payment_status === 'paid' ? 'success' : 'warning'}>
                  {conversation.linked_order.payment_status.replace(/_/g, ' ')}
                </Badge>
              </div>
              <Link
                className="text-sm text-accent hover:underline"
                to={`/orders/${conversation.linked_order.id}?shopId=${shopId}`}
              >
                Open order →
              </Link>
            </div>
          ) : conversation.customer_profile && conversation.customer_profile.previous_orders.length > 0 ? (
            <ul className="flex flex-col gap-1.5">
              {conversation.customer_profile.previous_orders.slice(0, 3).map((o) => (
                <li key={o.id} className="flex items-center justify-between gap-2 text-sm">
                  <span className="font-mono text-xs text-muted">#{o.id.slice(0, 8)}</span>
                  <span className="text-fg">{o.total_amount}</span>
                  <Badge tone={o.payment_status === 'paid' ? 'success' : 'warning'}>
                    {o.payment_status.replace(/_/g, ' ')}
                  </Badge>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No open orders" />
          )}
        </CardBody>
      </Card>

      {pendingReply ? (
        <Card>
          <CardHeader title="Suggested reply" description="Review the AI draft before sending. No auto-send." />
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

      <Card>
        <CardHeader title="Quick replies" description="Copy or insert a draft — review before sending." />
        <CardBody>
          <QuickReplyPanel shopId={shopId} customerContext={customerContext} />
        </CardBody>
      </Card>
    </div>
  );
}
