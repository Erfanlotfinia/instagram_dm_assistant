import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { NavLink } from 'react-router-dom';

import { AutomationStatusBadge } from './AutomationStatusBadge';
import { ChannelBadge } from './ChannelBadge';
import { FilterBar } from '../data';
import { Icons } from '../icons';
import { LoadingState, ErrorState, EmptyState } from '../data';
import { useShop } from '../../contexts/ShopContext';
import { queryKeys } from '../../lib/queryClient';
import { apiClient } from '../../services/apiClient';
import { useInboxStore } from '../../stores/inboxStore';
import { cn } from '../../lib/cn';
import type { Conversation, ConversationListFilters } from '../../types/conversation';

const QUICK_FILTERS: Array<{ key: keyof ConversationListFilters; label: string }> = [
  { key: 'needs_attention', label: 'Needs attention' },
  { key: 'handoff_required', label: 'Handoff' },
  { key: 'waiting_for_payment', label: 'Awaiting payment' },
  { key: 'unassigned', label: 'Unassigned' },
];

function customerName(conversation: Conversation): string {
  return (
    conversation.customer?.full_name ??
    conversation.customer?.instagram_user_id ??
    conversation.customer_id.slice(0, 8)
  );
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.round(hours / 24)}d`;
}

interface InboxListProps {
  activeId?: string;
}

export function InboxList({ activeId }: InboxListProps) {
  const { selectedShopId } = useShop();
  const { listFilters, setListFilters } = useInboxStore();
  const [search, setSearch] = useState('');

  const filters = useMemo<ConversationListFilters>(
    () => ({ ...listFilters, search: search || undefined }),
    [listFilters, search],
  );

  const query = useQuery({
    queryKey: queryKeys.conversations(selectedShopId, filters),
    queryFn: () => apiClient.listConversations(selectedShopId, filters),
    enabled: Boolean(selectedShopId),
    refetchInterval: 10_000,
  });

  const conversations = query.data ?? [];

  function toggleFilter(key: keyof ConversationListFilters) {
    setListFilters({ ...listFilters, [key]: listFilters[key] ? undefined : true });
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border p-3">
        <FilterBar search={search} onSearch={setSearch} searchPlaceholder="Search conversations…" />
        <div className="mt-2 flex flex-wrap gap-1.5">
          {QUICK_FILTERS.map((filter) => {
            const active = Boolean(listFilters[filter.key]);
            return (
              <button
                key={filter.key}
                type="button"
                onClick={() => toggleFilter(filter.key)}
                className={cn(
                  'rounded-full border px-2.5 py-1 text-xs font-medium transition-colors',
                  active
                    ? 'border-accent bg-accent-soft text-accent'
                    : 'border-border text-muted hover:text-fg',
                )}
              >
                {filter.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {query.isLoading ? (
          <LoadingState />
        ) : query.error ? (
          <ErrorState message={query.error instanceof Error ? query.error.message : 'Failed to load'} />
        ) : conversations.length === 0 ? (
          <EmptyState title="No conversations" description="Adjust filters or wait for new messages." />
        ) : (
          <ul>
            {conversations.map((conversation) => (
              <li key={conversation.id}>
                <NavLink
                  to={`/inbox/${conversation.id}?shopId=${selectedShopId}`}
                  className={cn(
                    'block border-b border-border/70 px-3 py-3 transition-colors hover:bg-surface-sunken',
                    conversation.id === activeId && 'bg-accent-soft',
                    conversation.needs_attention && 'border-l-2 border-l-danger',
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-2">
                      <ChannelBadge channel={conversation.channel_provider} />
                      <span className="truncate text-sm font-medium text-fg">{customerName(conversation)}</span>
                    </div>
                    <span className="shrink-0 text-xs text-subtle">
                      {relativeTime(conversation.last_message_at ?? conversation.updated_at)}
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-1 text-xs text-muted">
                    {conversation.last_message_text ?? 'No messages yet'}
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <AutomationStatusBadge conversation={conversation} />
                    {conversation.last_intent ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-surface-sunken px-2 py-0.5 text-xs text-muted">
                        <Icons.spark size={11} />
                        {conversation.last_intent}
                      </span>
                    ) : null}
                    {conversation.linked_product ? (
                      <span className="inline-flex items-center gap-1 truncate rounded-full bg-surface-sunken px-2 py-0.5 text-xs text-muted">
                        <Icons.catalog size={11} />
                        <span className="max-w-[120px] truncate">{conversation.linked_product.title}</span>
                      </span>
                    ) : null}
                  </div>
                </NavLink>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
