import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { Badge, Button, FilterChip, Select } from '../components/ui';
import { DataTable, FilterBar, KpiCard, type Column } from '../components/data';
import { HubPage } from '../components/shell/HubPage';
import { ChannelBadge } from '../components/inbox/ChannelBadge';
import { useShop } from '../contexts/ShopContext';
import { useAuth } from '../contexts/AuthContext';
import { useOperatorWorkspace } from '../lib/useOperatorWorkspace';
import { SlaBadge } from '../components/operator/AssignmentControls';
import type {
  OperatorConversationPriority,
  OperatorQueueItem,
  OperatorQueueStatus,
  OperatorSlaState,
} from '../types/sprint5Operator';

interface OperatorWorkspaceViewProps {
  defaultFilter?: 'assigned_to_me' | 'all';
}

const STATUS_OPTIONS: { id: OperatorQueueStatus | 'all'; label: string }[] = [
  { id: 'all', label: 'All statuses' },
  { id: 'needs_attention', label: 'Needs attention' },
  { id: 'waiting_operator', label: 'Waiting on operator' },
  { id: 'waiting_customer', label: 'Waiting on customer' },
  { id: 'unassigned', label: 'Unassigned' },
  { id: 'assigned', label: 'Assigned' },
  { id: 'escalated', label: 'Escalated' },
  { id: 'resolved', label: 'Resolved' },
];

const PRIORITY_OPTIONS: { id: OperatorConversationPriority | 'all'; label: string }[] = [
  { id: 'all', label: 'All priorities' },
  { id: 'urgent', label: 'Urgent' },
  { id: 'high', label: 'High' },
  { id: 'normal', label: 'Normal' },
  { id: 'low', label: 'Low' },
];

const SLA_OPTIONS: { id: OperatorSlaState | 'all'; label: string }[] = [
  { id: 'all', label: 'All SLA' },
  { id: 'breached', label: 'Breached' },
  { id: 'approaching_breach', label: 'Approaching' },
  { id: 'within_sla', label: 'Within SLA' },
  { id: 'unknown', label: 'Unknown' },
];

const CHANNEL_OPTIONS = [
  { id: 'all', label: 'All channels' },
  { id: 'instagram', label: 'Instagram' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'telegram', label: 'Telegram' },
  { id: 'bale', label: 'Bale' },
  { id: 'rubika', label: 'Rubika' },
  { id: 'web_chat', label: 'Web Chat' },
];

function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const ms = new Date(iso).getTime();
  if (Number.isNaN(ms)) return '—';
  const diff = Date.now() - ms;
  const minutes = Math.round(diff / 60_000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

const STATUS_TONE: Record<OperatorQueueStatus, 'neutral' | 'warning' | 'danger' | 'success' | 'accent' | 'info'> = {
  needs_attention: 'danger',
  waiting_operator: 'warning',
  waiting_customer: 'neutral',
  assigned: 'accent',
  unassigned: 'warning',
  resolved: 'success',
  escalated: 'danger',
};

const PRIORITY_TONE: Record<OperatorConversationPriority, 'danger' | 'warning' | 'neutral' | 'accent'> = {
  urgent: 'danger',
  high: 'warning',
  normal: 'neutral',
  low: 'accent',
};

export function OperatorWorkspacePage() {
  return <OperatorWorkspaceView defaultFilter="all" />;
}

/** Sprint 5 — My Queue: the workspace pre-filtered to "assigned to me". */
export function OperatorMyQueuePage() {
  return <OperatorWorkspaceView defaultFilter="assigned_to_me" />;
}

function OperatorWorkspaceView({ defaultFilter = 'all' }: OperatorWorkspaceViewProps) {
  const { selectedShopId } = useShop();
  const { user } = useAuth();
  const { summary, queueItems, isLoading, error, warnings } = useOperatorWorkspace(selectedShopId);

  const [statusFilter, setStatusFilter] = useState<OperatorQueueStatus | 'all'>('all');
  const [priorityFilter, setPriorityFilter] = useState<OperatorConversationPriority | 'all'>('all');
  const [slaFilter, setSlaFilter] = useState<OperatorSlaState | 'all'>('all');
  const [channelFilter, setChannelFilter] = useState<string>('all');
  const [assignedToMeOnly, setAssignedToMeOnly] = useState<boolean>(defaultFilter === 'assigned_to_me');
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return queueItems.filter((item) => {
      if (statusFilter !== 'all' && item.status !== statusFilter) return false;
      if (priorityFilter !== 'all' && item.priority !== priorityFilter) return false;
      if (slaFilter !== 'all' && item.sla_state !== slaFilter) return false;
      if (channelFilter !== 'all' && (item.channel_provider ?? '') !== channelFilter) return false;
      if (assignedToMeOnly && (!user || item.assigned_operator_id !== user.id)) return false;
      if (q) {
        const haystack = `${item.customer_label} ${item.last_message_preview ?? ''} ${item.ai_summary ?? ''}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [queueItems, statusFilter, priorityFilter, slaFilter, channelFilter, assignedToMeOnly, search, user]);

  const columns: Column<OperatorQueueItem>[] = [
    {
      key: 'priority',
      header: 'Priority',
      render: (row) => <Badge tone={PRIORITY_TONE[row.priority]}>{row.priority}</Badge>,
    },
    {
      key: 'customer',
      header: 'Customer',
      render: (row) => <span className="font-medium text-fg">{row.customer_label}</span>,
    },
    {
      key: 'channel',
      header: 'Channel',
      render: (row) => <ChannelBadge channel={row.channel_provider} showLabel />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <Badge tone={STATUS_TONE[row.status]}>{row.status.replace(/_/g, ' ')}</Badge>
      ),
    },
    {
      key: 'sla',
      header: 'SLA',
      render: (row) => <SlaBadge state={row.sla_state} waitingMinutes={row.waiting_minutes} />,
    },
    {
      key: 'assigned',
      header: 'Assigned to',
      render: (row) =>
        row.assigned_operator_id ? (
          <span className="text-sm text-fg">
            {row.assigned_operator_name ?? row.assigned_operator_id.slice(0, 8)}
          </span>
        ) : (
          <Badge tone="warning" dot>
            Unassigned
          </Badge>
        ),
    },
    {
      key: 'last',
      header: 'Last message',
      render: (row) => (
        <div className="flex flex-col">
          <span className="line-clamp-1 max-w-[220px] text-xs text-muted">
            {row.last_message_preview ?? '—'}
          </span>
          <span className="text-xs text-subtle">{formatRelativeTime(row.last_inbound_at)}</span>
        </div>
      ),
    },
    {
      key: 'ai',
      header: 'AI summary',
      render: (row) =>
        row.ai_summary ? (
          <span className="line-clamp-1 max-w-[200px] text-xs text-muted">{row.ai_summary}</span>
        ) : (
          <span className="text-xs text-subtle">—</span>
        ),
    },
    {
      key: 'actions',
      header: 'Actions',
      align: 'right',
      render: (row) => (
        <div className="flex flex-wrap items-center justify-end gap-1.5">
          <Link to={row.action_to}>
            <Button size="sm" variant="secondary">
              Open
            </Button>
          </Link>
          <Link to={`/inbox/${row.conversation_id}/intelligence`}>
            <Button size="sm" variant="ghost">
              AI
            </Button>
          </Link>
        </div>
      ),
    },
  ];

  const error_ = error instanceof Error ? error.message : error ? 'Failed to load operator workspace.' : null;

  return (
    <HubPage
      eyebrow="Operations"
      title="Operator Workspace"
      description="Prioritized conversations, handoffs, SLA risk, and reply tools for daily support operations."
      actions={
        <Badge tone={summary.breached_sla_count > 0 ? 'danger' : 'success'}>
          {queueItems.length} conversations
        </Badge>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <KpiCard label="Needs attention" value={summary.needs_attention_count} tone="danger" />
        <KpiCard label="Breached SLA" value={summary.breached_sla_count} tone="danger" />
        <KpiCard label="Unassigned" value={summary.unassigned_count} tone="warning" />
        <KpiCard label="Assigned to me" value={summary.assigned_to_me_count} tone="accent" />
        <KpiCard label="High priority" value={summary.high_priority_count} tone="warning" />
      </div>

      <FilterBar search={search} onSearch={setSearch} searchPlaceholder="Search customer or message…">
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as OperatorQueueStatus | 'all')}
          aria-label="Status filter"
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </Select>
        <Select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value as OperatorConversationPriority | 'all')}
          aria-label="Priority filter"
        >
          {PRIORITY_OPTIONS.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </Select>
        <Select
          value={slaFilter}
          onChange={(e) => setSlaFilter(e.target.value as OperatorSlaState | 'all')}
          aria-label="SLA filter"
        >
          {SLA_OPTIONS.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </Select>
        <Select
          value={channelFilter}
          onChange={(e) => setChannelFilter(e.target.value)}
          aria-label="Channel filter"
        >
          {CHANNEL_OPTIONS.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </Select>
        <FilterChip
          active={assignedToMeOnly}
          onClick={() => setAssignedToMeOnly((v) => !v)}
        >
          Assigned to me
        </FilterChip>
      </FilterBar>

      {warnings.length > 0 ? (
        <div className="rounded-lg border border-warning/30 bg-warning-soft/30 p-3 text-xs text-warning">
          {warnings.map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      ) : null}

      <DataTable
        rows={filtered}
        rowKey={(row) => row.conversation_id}
        columns={columns}
        isLoading={isLoading}
        error={error_}
        emptyTitle="No conversations match"
        emptyDescription="Adjust filters or check back later — the queue refreshes automatically."
        rowClassName={(row) =>
          row.sla_state === 'breached' ? 'bg-danger-soft/30' : row.status === 'needs_attention' ? 'bg-warning-soft/20' : undefined
        }
      />

      <p className="text-xs text-subtle">
        Assignment actions are available on each conversation in the operator context panel. No auto-send.
      </p>
    </HubPage>
  );
}
