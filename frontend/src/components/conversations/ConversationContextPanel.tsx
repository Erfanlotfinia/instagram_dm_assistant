import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { OrderDraftPanel } from '../orders/OrderDraftPanel';
import { queryKeys } from '../../lib/queryClient';
import { apiClient } from '../../services/apiClient';
import type { ConversationDetail, ConversationEvent, CustomerUpdate } from '../../types/conversation';
import { ConversationEventsTimeline } from './ConversationEventsTimeline';
import { CustomerProfilePanel } from './CustomerProfilePanel';

type ContextTab = 'customer' | 'order' | 'agent' | 'activity';

interface ConversationContextPanelProps {
  conversation: ConversationDetail;
  shopId: string;
  confidence: Record<string, unknown> | undefined;
  onSaveCustomer: (values: CustomerUpdate) => void;
  isSavingCustomer: boolean;
}

const TABS: { id: ContextTab; label: string }[] = [
  { id: 'customer', label: 'Customer' },
  { id: 'order', label: 'Order' },
  { id: 'agent', label: 'Agent intel' },
  { id: 'activity', label: 'Activity' },
];

function formatWorkflowLabel(value: string): string {
  return value.replace(/_/g, ' ');
}

export function ConversationContextPanel({
  conversation,
  shopId,
  confidence,
  onSaveCustomer,
  isSavingCustomer,
}: ConversationContextPanelProps) {
  const [activeTab, setActiveTab] = useState<ContextTab>('customer');
  const linkedOrderId = conversation.linked_order?.id;
  const correctnessQuery = useQuery({
    queryKey: queryKeys.orderCorrectness(linkedOrderId ?? ''),
    queryFn: () => apiClient.getOrderCorrectness(linkedOrderId!),
    enabled: Boolean(linkedOrderId),
  });

  return (
    <aside className="conversation-context" aria-label="Conversation context">
      <div className="conversation-context__tabs" role="tablist" aria-label="Context sections">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`context-tab-${tab.id}`}
            aria-selected={activeTab === tab.id}
            aria-controls={`context-panel-${tab.id}`}
            className={`conversation-context__tab${activeTab === tab.id ? ' conversation-context__tab--active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div
        id="context-panel-customer"
        role="tabpanel"
        aria-labelledby="context-tab-customer"
        hidden={activeTab !== 'customer'}
        className="conversation-context__panel"
      >
        <CustomerProfilePanel
          profile={conversation.customer_profile ?? null}
          onSave={onSaveCustomer}
          isSaving={isSavingCustomer}
        />
      </div>

      <div
        id="context-panel-order"
        role="tabpanel"
        aria-labelledby="context-tab-order"
        hidden={activeTab !== 'order'}
        className="conversation-context__panel"
      >
        {conversation.linked_order ? (
          <div className="order-summary">
            <div className="order-summary__identity">
              <p className="order-summary__eyebrow">Linked order</p>
              <p className="order-summary__id">#{conversation.linked_order.id.slice(0, 8)}</p>
            </div>
            <div className="order-summary__status">
              <span className="status-pill status-pill--neutral">
                {formatWorkflowLabel(conversation.linked_order.status)}
              </span>
              <span
                className={`status-pill${
                  conversation.linked_order.payment_status === 'paid'
                    ? ' status-pill--success'
                    : ' status-pill--warning'
                }`}
              >
                {formatWorkflowLabel(conversation.linked_order.payment_status)}
              </span>
            </div>
            <Link
              className="order-summary__open"
              to={`/orders/${conversation.linked_order.id}?shopId=${shopId}`}
            >
              Open order →
            </Link>
          </div>
        ) : (
          <p className="empty-state">No active order linked to this conversation.</p>
        )}

        {correctnessQuery.data ? (
          <OrderDraftPanel order={correctnessQuery.data} />
        ) : null}
      </div>

      <div
        id="context-panel-agent"
        role="tabpanel"
        aria-labelledby="context-tab-agent"
        hidden={activeTab !== 'agent'}
        className="conversation-context__panel"
      >
        <div className="context-section">
          <h3 className="context-section__title">Extracted slots</h3>
          {conversation.slots ? (
            <dl className="context-facts">
              <div className="context-facts__item">
                <dt>Product</dt>
                <dd>{conversation.linked_product?.title ?? conversation.slots.product_id ?? '—'}</dd>
              </div>
              <div className="context-facts__item">
                <dt>Variant</dt>
                <dd>{conversation.slots.product_variant_id ?? '—'}</dd>
              </div>
              <div className="context-facts__item">
                <dt>Color</dt>
                <dd>{conversation.slots.color ?? '—'}</dd>
              </div>
              <div className="context-facts__item">
                <dt>Size</dt>
                <dd>{conversation.slots.size ?? '—'}</dd>
              </div>
              <div className="context-facts__item">
                <dt>Quantity</dt>
                <dd>{conversation.slots.quantity ?? '—'}</dd>
              </div>
              <div className="context-facts__item context-facts__item--wide">
                <dt>Missing fields</dt>
                <dd>{conversation.slots.missing_fields.join(', ') || 'None'}</dd>
              </div>
            </dl>
          ) : (
            <p className="empty-state">No extracted slots yet.</p>
          )}
        </div>

        <div className="context-section">
          <h3 className="context-section__title">Inventory</h3>
          {conversation.inventory_status ? (
            <dl className="context-facts">
              <div className="context-facts__item">
                <dt>Availability</dt>
                <dd>
                  <span
                    className={`status-pill${
                      conversation.inventory_status.in_stock ? ' status-pill--success' : ' status-pill--danger'
                    }`}
                  >
                    {conversation.inventory_status.in_stock ? 'In stock' : 'Out of stock'}
                  </span>
                </dd>
              </div>
              <div className="context-facts__item">
                <dt>Available qty</dt>
                <dd>{conversation.inventory_status.available_quantity ?? '—'}</dd>
              </div>
            </dl>
          ) : (
            <p className="empty-state">No variant selected.</p>
          )}
        </div>

        {confidence ? (
          <div className="context-section">
            <h3 className="context-section__title">Confidence</h3>
            <dl className="context-facts">
              <div className="context-facts__item">
                <dt>Intent</dt>
                <dd>{String(confidence.intent ?? '—')}</dd>
              </div>
              <div className="context-facts__item">
                <dt>Slots</dt>
                <dd>{String(confidence.slots ?? '—')}</dd>
              </div>
            </dl>
          </div>
        ) : null}

        <div className="context-section">
          <h3 className="context-section__title">Decision trace</h3>
          <p className="context-section__body">
            {conversation.decision_trace_summary ?? 'No agent actions yet.'}
          </p>
        </div>
      </div>

      <div
        id="context-panel-activity"
        role="tabpanel"
        aria-labelledby="context-tab-activity"
        hidden={activeTab !== 'activity'}
        className="conversation-context__panel conversation-context__panel--activity"
      >
        <div className="activity-panel__head">
          <h2 className="activity-panel__title">Activity</h2>
          <span className="activity-panel__count">
            {(conversation.events ?? []).length} {(conversation.events ?? []).length === 1 ? 'event' : 'events'}
          </span>
        </div>
        <ConversationEventsTimeline events={(conversation.events ?? []) as ConversationEvent[]} />
      </div>
    </aside>
  );
}
