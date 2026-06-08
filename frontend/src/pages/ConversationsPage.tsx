import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { Pagination, paginateItems } from '../components/Pagination';
import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { ConversationListFilters, ConversationState } from '../types/conversation';

const PAGE_SIZE = 15;

const STATE_OPTIONS: { value: ConversationState | ''; label: string }[] = [
  { value: '', label: 'All states' },
  { value: 'open', label: 'Open' },
  { value: 'pending_handoff', label: 'Pending handoff' },
  { value: 'closed', label: 'Closed' },
  { value: 'archived', label: 'Archived' },
];

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
        <h1>Conversations</h1>
        <p>Monitor Instagram DM threads, handoff state, and latest customer messages.</p>
        <ShopSelector />

        <div className="filter-grid">
          <label className="form-field">
            <span>State</span>
            <select
              value={filters.state ?? ''}
              onChange={(event) => {
                setPage(1);
                setFilters((current) => ({
                  ...current,
                  state: (event.target.value as ConversationState) || undefined,
                }));
              }}
            >
              {STATE_OPTIONS.map((option) => (
                <option key={option.label} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="form-field">
            <span>Handoff</span>
            <select
              value={
                filters.handoff_required === undefined ? '' : filters.handoff_required ? 'yes' : 'no'
              }
              onChange={(event) => {
                setPage(1);
                const value = event.target.value;
                setFilters((current) => ({
                  ...current,
                  handoff_required: value === '' ? undefined : value === 'yes',
                }));
              }}
            >
              <option value="">All</option>
              <option value="yes">Handoff required</option>
              <option value="no">No handoff</option>
            </select>
          </label>

          <label className="form-field">
            <span>Search customer</span>
            <input
              type="search"
              placeholder="Name or Instagram ID"
              value={filters.search ?? ''}
              onChange={(event) => {
                setPage(1);
                setFilters((current) => ({
                  ...current,
                  search: event.target.value || undefined,
                }));
              }}
            />
          </label>

          <label className="form-field">
            <span>Updated from</span>
            <input
              type="date"
              value={filters.updated_from?.slice(0, 10) ?? ''}
              onChange={(event) => {
                setPage(1);
                setFilters((current) => ({
                  ...current,
                  updated_from: event.target.value ? `${event.target.value}T00:00:00Z` : undefined,
                }));
              }}
            />
          </label>
        </div>
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
                <th>Customer</th>
                <th>State</th>
                <th>Last message</th>
                <th>Confidence</th>
                <th>Handoff</th>
                <th>Badges</th>
                <th>Last update</th>
              </tr>
            </thead>
            <tbody>
              {pageItems.map((conversation) => (
                <tr key={conversation.id}>
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
                  <td>{conversation.state}</td>
                  <td>{conversation.last_message_text ?? '—'}</td>
                  <td>
                    {conversation.confidence_score != null
                      ? conversation.confidence_score.toFixed(2)
                      : '—'}
                  </td>
                  <td>{conversation.handoff_required ? 'yes' : 'no'}</td>
                  <td>
                    <div className="button-row" aria-label="Conversation badges">
                      {!conversation.preview_required && !conversation.handoff_required ? <span className="status-pill">Auto</span> : null}
                      {conversation.preview_required ? <span className="status-pill">Preview required</span> : null}
                      {conversation.handoff_required ? <span className="status-pill">Human handoff</span> : null}
                      {conversation.agent_mode === 'copilot' ? <span className="status-pill">Copilot</span> : null}
                      {conversation.agent_mode === 'human_first' ? <span className="status-pill">Human-first</span> : null}
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
