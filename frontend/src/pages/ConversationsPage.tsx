import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ConversationFilters } from '../components/conversations/ConversationFilters';
import { PriorityBadge } from '../components/conversations/PriorityBadge';
import { Pagination, paginateItems } from '../components/Pagination';
import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { ConversationListFilters } from '../types/conversation';

const PAGE_SIZE = 15;

export function ConversationsPage() {
  const { selectedShopId } = useShop();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<ConversationListFilters>({});

  const conversationsQuery = useQuery({
    queryKey: queryKeys.conversations(selectedShopId, filters),
    queryFn: () => apiClient.listConversations(selectedShopId, filters),
    enabled: Boolean(selectedShopId),
  });

  const conversations = conversationsQuery.data ?? [];
  const pageItems = useMemo(
    () => paginateItems(conversations, page, PAGE_SIZE),
    [conversations, page],
  );

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Inbox</p>
        <h1>Smart Conversation Queue</h1>
        <p>Prioritized inbox for daily operator workflows — handoffs, payments, and urgent threads.</p>
        <ShopSelector />
        <ConversationFilters
          filters={filters}
          onChange={(next) => {
            setPage(1);
            setFilters(next);
          }}
        />
      </section>

      <section className="dashboard-card dashboard-card--wide">
        {conversationsQuery.isLoading ? <p className="loading-state">Loading conversations...</p> : null}
        {conversationsQuery.error ? (
          <p className="form-error">
            {conversationsQuery.error instanceof Error
              ? conversationsQuery.error.message
              : 'Failed to load conversations'}
          </p>
        ) : null}

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Customer</th>
                <th>Channel</th>
                <th>Last message</th>
                <th>Product</th>
                <th>Order</th>
                <th>Payment</th>
                <th>Operator</th>
                <th>Badges</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {pageItems.map((conversation) => (
                <tr
                  key={conversation.id}
                  className={conversation.needs_attention ? 'data-table__row--attention' : undefined}
                >
                  <td>
                    <PriorityBadge
                      level={conversation.priority_level}
                      score={conversation.priority_score}
                      reason={conversation.priority_reason}
                    />
                  </td>
                  <td>
                    <Link
                      className="table-link"
                      to={`/conversations/${conversation.id}?shopId=${selectedShopId}`}
                    >
                      {conversation.customer?.full_name ??
                        conversation.customer?.instagram_user_id ??
                        conversation.customer_id}
                    </Link>
                  </td>
                  <td>
                    <span className="status-pill">{conversation.channel_provider ?? 'instagram'}</span>
                    <div className="muted-text">{conversation.channel_conversation_id ?? conversation.channel_customer_id ?? '—'}</div>
                  </td>
                  <td>{conversation.last_message_text ?? '—'}</td>
                  <td>{conversation.linked_product?.title ?? '—'}</td>
                  <td>{conversation.linked_order?.status ?? '—'}</td>
                  <td>{conversation.linked_order?.payment_status ?? '—'}</td>
                  <td>{conversation.assigned_operator?.full_name ?? '—'}</td>
                  <td>
                    <div className="button-row" aria-label="Conversation badges">
                      {conversation.handoff_required ? (
                        <span className="status-pill">Handoff</span>
                      ) : null}
                      {conversation.agent_paused ? <span className="status-pill">Human</span> : null}
                      {!conversation.preview_required && !conversation.handoff_required ? (
                        <span className="status-pill">Auto</span>
                      ) : null}
                      {conversation.preview_required ? (
                        <span className="status-pill">Preview</span>
                      ) : null}
                      {conversation.is_simulation ? <span className="status-pill">Sim</span> : null}
                      {conversation.agent_mode === 'copilot' ? (
                        <span className="status-pill">Copilot</span>
                      ) : null}
                      {conversation.agent_mode === 'human_first' ? (
                        <span className="status-pill">Human-first</span>
                      ) : null}
                    </div>
                  </td>
                  <td>{new Date(conversation.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {conversations.length === 0 && !conversationsQuery.isLoading ? (
            <p className="empty-state">No conversations match the current filters.</p>
          ) : null}
        </div>

        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          totalItems={conversations.length}
          onPageChange={setPage}
        />
      </section>
    </div>
  );
}
