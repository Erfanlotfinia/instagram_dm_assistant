import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { Badge, Button, Select } from '../ui';
import { apiClient } from '../../services/apiClient';
import { useAssignConversation } from '../../lib/useAssignConversation';
import { useAuth } from '../../contexts/AuthContext';
import { queryKeys } from '../../lib/queryClient';
import { cn } from '../../lib/cn';

interface AssignmentControlsProps {
  shopId: string;
  conversationId: string;
  assignedOperatorId?: string | null;
  assignedOperatorName?: string | null;
  size?: 'sm' | 'md';
}

/**
 * Sprint 5 — shared assignment controls. Operators can assign to themselves;
 * admins/owners can assign to any shop member via a picker. Uses the existing
 * `POST /conversations/{id}/assign` mutation with optimistic invalidation.
 */
export function AssignmentControls({
  shopId,
  conversationId,
  assignedOperatorId,
  assignedOperatorName,
  size = 'sm',
}: AssignmentControlsProps) {
  const { user } = useAuth();
  const { assign, isPending } = useAssignConversation({ shopId, conversationId });
  const [pickerOpen, setPickerOpen] = useState(false);
  const [selectedOperator, setSelectedOperator] = useState('');

  const membersQuery = useQuery({
    queryKey: queryKeys.shopMembers(shopId),
    queryFn: () => apiClient.listShopMembers(shopId),
    enabled: Boolean(shopId) && (user?.role === 'admin' || user?.role === 'owner'),
  });

  const isAssignedToMe = Boolean(user && assignedOperatorId && assignedOperatorId === user.id);
  const canAssignOthers = user?.role === 'admin' || user?.role === 'owner';
  const buttonSize = size === 'sm' ? 'sm' : 'md';

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-muted">Assigned:</span>
        {assignedOperatorId ? (
          <Badge tone={isAssignedToMe ? 'accent' : 'neutral'}>
            {assignedOperatorName ?? assignedOperatorId.slice(0, 8)}
            {isAssignedToMe ? ' (you)' : ''}
          </Badge>
        ) : (
          <Badge tone="warning" dot>
            Unassigned
          </Badge>
        )}
      </div>

      {!isAssignedToMe ? (
        <Button
          size={buttonSize}
          variant="secondary"
          disabled={isPending || !user}
          onClick={() => user && assign(user.id)}
        >
          {isPending ? 'Assigning…' : 'Assign to me'}
        </Button>
      ) : null}

      {canAssignOthers ? (
        pickerOpen ? (
          <div className="flex items-center gap-1.5">
            <Select
              value={selectedOperator}
              onChange={(e) => setSelectedOperator(e.target.value)}
              aria-label="Assign to operator"
              className="h-8 text-xs"
            >
              <option value="">Select operator…</option>
              {(membersQuery.data ?? []).map((m) => (
                <option key={m.id} value={m.user_id}>
                  {m.full_name || m.email}
                </option>
              ))}
            </Select>
            <Button
              size={buttonSize}
              disabled={isPending || !selectedOperator}
              onClick={() => {
                assign(selectedOperator);
                setPickerOpen(false);
                setSelectedOperator('');
              }}
            >
              Assign
            </Button>
            <Button
              size={buttonSize}
              variant="ghost"
              onClick={() => {
                setPickerOpen(false);
                setSelectedOperator('');
              }}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <Button size={buttonSize} variant="ghost" onClick={() => setPickerOpen(true)}>
            Change operator
          </Button>
        )
      ) : null}
    </div>
  );
}

/** Small badge summarizing SLA state, used by the queue and the conversation panel. */
export function SlaBadge({
  state,
  waitingMinutes,
  className,
}: {
  state: 'within_sla' | 'approaching_breach' | 'breached' | 'unknown';
  waitingMinutes?: number | null;
  className?: string;
}) {
  const tone = state === 'breached' ? 'danger' : state === 'approaching_breach' ? 'warning' : state === 'within_sla' ? 'success' : 'neutral';
  const label =
    state === 'breached'
      ? 'Breached'
      : state === 'approaching_breach'
        ? 'Approaching'
        : state === 'within_sla'
          ? 'Within SLA'
          : 'SLA unknown';
  const wait =
    waitingMinutes != null ? (waitingMinutes < 60 ? `${waitingMinutes}m` : `${Math.round(waitingMinutes / 60)}h`) : null;
  return (
    <Badge tone={tone} className={cn(className)}>
      {label}
      {wait ? ` · ${wait} waiting` : ''}
    </Badge>
  );
}
