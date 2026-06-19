import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { OrderDraftPanel } from '../orders/OrderDraftPanel';
import { Badge } from '../ui';
import { queryKeys } from '../../lib/queryClient';
import { cn } from '../../lib/cn';
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

function FactGrid({ children }: { children: React.ReactNode }) {
  return <dl className="grid gap-3 text-sm sm:grid-cols-2">{children}</dl>;
}

function FactItem({ label, value, wide }: { label: string; value: React.ReactNode; wide?: boolean }) {
  return (
    <div className={cn('flex flex-col gap-0.5', wide && 'sm:col-span-2')}>
      <dt className="text-xs font-medium text-muted">{label}</dt>
      <dd className="text-fg">{value}</dd>
    </div>
  );
}

function ContextSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3 border-b border-border pb-4 last:border-0 last:pb-0">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</h3>
      {children}
    </section>
  );
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
    <aside className="flex h-full flex-col border-l border-border bg-surface" aria-label="Conversation context">
      <div className="flex gap-0.5 overflow-x-auto border-b border-border px-2" role="tablist" aria-label="Context sections">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`context-tab-${tab.id}`}
            aria-selected={activeTab === tab.id}
            aria-controls={`context-panel-${tab.id}`}
            className={cn(
              '-mb-px whitespace-nowrap border-b-2 px-3 py-2.5 text-xs font-medium transition-colors',
              activeTab === tab.id ? 'border-accent text-fg' : 'border-transparent text-muted hover:text-fg',
            )}
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
        className="flex-1 overflow-y-auto p-4"
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
        className="flex flex-1 flex-col gap-4 overflow-y-auto p-4"
      >
        {conversation.linked_order ? (
          <div className="rounded-lg border border-border bg-surface-sunken p-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium text-muted">Linked order</p>
                <p className="font-mono text-sm font-semibold text-fg">#{conversation.linked_order.id.slice(0, 8)}</p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                <Badge tone="neutral">{formatWorkflowLabel(conversation.linked_order.status)}</Badge>
                <Badge tone={conversation.linked_order.payment_status === 'paid' ? 'success' : 'warning'}>
                  {formatWorkflowLabel(conversation.linked_order.payment_status)}
                </Badge>
              </div>
            </div>
            <Link
              className="mt-2 inline-block text-sm text-accent hover:underline"
              to={`/orders/${conversation.linked_order.id}?shopId=${shopId}`}
            >
              Open order →
            </Link>
          </div>
        ) : (
          <p className="text-sm text-muted">No active order linked to this conversation.</p>
        )}

        {correctnessQuery.data ? <OrderDraftPanel order={correctnessQuery.data} /> : null}
      </div>

      <div
        id="context-panel-agent"
        role="tabpanel"
        aria-labelledby="context-tab-agent"
        hidden={activeTab !== 'agent'}
        className="flex flex-1 flex-col gap-4 overflow-y-auto p-4"
      >
        <ContextSection title="Extracted slots">
          {conversation.slots ? (
            <FactGrid>
              <FactItem label="Product" value={conversation.linked_product?.title ?? conversation.slots.product_id ?? '—'} />
              <FactItem label="Variant" value={conversation.slots.product_variant_id ?? '—'} />
              <FactItem label="Color" value={conversation.slots.color ?? '—'} />
              <FactItem label="Size" value={conversation.slots.size ?? '—'} />
              <FactItem label="Quantity" value={conversation.slots.quantity ?? '—'} />
              <FactItem
                label="Missing fields"
                value={conversation.slots.missing_fields.join(', ') || 'None'}
                wide
              />
            </FactGrid>
          ) : (
            <p className="text-sm text-muted">No extracted slots yet.</p>
          )}
        </ContextSection>

        <ContextSection title="Inventory">
          {conversation.inventory_status ? (
            <FactGrid>
              <FactItem
                label="Availability"
                value={
                  <Badge tone={conversation.inventory_status.in_stock ? 'success' : 'danger'}>
                    {conversation.inventory_status.in_stock ? 'In stock' : 'Out of stock'}
                  </Badge>
                }
              />
              <FactItem label="Available qty" value={conversation.inventory_status.available_quantity ?? '—'} />
            </FactGrid>
          ) : (
            <p className="text-sm text-muted">No variant selected.</p>
          )}
        </ContextSection>

        {confidence ? (
          <ContextSection title="Confidence">
            <FactGrid>
              <FactItem label="Intent" value={String(confidence.intent ?? '—')} />
              <FactItem label="Slots" value={String(confidence.slots ?? '—')} />
            </FactGrid>
          </ContextSection>
        ) : null}

        <ContextSection title="Decision trace">
          <p className="text-sm text-fg">{conversation.decision_trace_summary ?? 'No agent actions yet.'}</p>
        </ContextSection>
      </div>

      <div
        id="context-panel-activity"
        role="tabpanel"
        aria-labelledby="context-tab-activity"
        hidden={activeTab !== 'activity'}
        className="flex flex-1 flex-col overflow-y-auto p-4"
      >
        <div className="mb-3 flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-fg">Activity</h2>
          <span className="text-xs text-muted">
            {(conversation.events ?? []).length} {(conversation.events ?? []).length === 1 ? 'event' : 'events'}
          </span>
        </div>
        <ConversationEventsTimeline events={(conversation.events ?? []) as ConversationEvent[]} />
      </div>
    </aside>
  );
}
