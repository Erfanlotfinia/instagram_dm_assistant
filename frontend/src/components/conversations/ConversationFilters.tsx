import type { ConversationListFilters, ConversationState } from '../../types/conversation';

const STATE_OPTIONS: { value: ConversationState | ''; label: string }[] = [
  { value: '', label: 'All states' },
  { value: 'open', label: 'Open' },
  { value: 'pending_handoff', label: 'Pending handoff' },
  { value: 'closed', label: 'Closed' },
  { value: 'archived', label: 'Archived' },
];

interface ConversationFiltersProps {
  filters: ConversationListFilters;
  onChange: (filters: ConversationListFilters) => void;
}

export function ConversationFilters({ filters, onChange }: ConversationFiltersProps) {
  function update(partial: Partial<ConversationListFilters>) {
    onChange({ ...filters, ...partial });
  }

  function toggleFlag(key: keyof ConversationListFilters) {
    update({ [key]: filters[key] ? undefined : true });
  }

  return (
    <div className="filter-grid filter-grid--inbox">
      <label className="form-field">
        <span>State</span>
        <select
          value={filters.state ?? ''}
          onChange={(event) =>
            update({ state: (event.target.value as ConversationState) || undefined })
          }
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
          value={filters.handoff_required === undefined ? '' : filters.handoff_required ? 'yes' : 'no'}
          onChange={(event) => {
            const value = event.target.value;
            update({ handoff_required: value === '' ? undefined : value === 'yes' });
          }}
        >
          <option value="">All</option>
          <option value="yes">Handoff required</option>
          <option value="no">No handoff</option>
        </select>
      </label>

      <label className="form-field">
        <span>Simulation</span>
        <select
          value={filters.is_simulation === undefined ? '' : filters.is_simulation ? 'sim' : 'real'}
          onChange={(event) => {
            const value = event.target.value;
            update({
              is_simulation: value === '' ? undefined : value === 'sim',
            });
          }}
        >
          <option value="">All</option>
          <option value="real">Real conversations</option>
          <option value="sim">Simulation only</option>
        </select>
      </label>

      <label className="form-field form-field--wide">
        <span>Search</span>
        <input
          type="search"
          placeholder="Customer, phone, order ID, product"
          value={filters.search ?? ''}
          onChange={(event) => update({ search: event.target.value || undefined })}
        />
      </label>

      <label className="form-field">
        <span>Updated from</span>
        <input
          type="date"
          value={filters.updated_from?.slice(0, 10) ?? ''}
          onChange={(event) =>
            update({
              updated_from: event.target.value ? `${event.target.value}T00:00:00Z` : undefined,
            })
          }
        />
      </label>

      <div className="filter-chips" role="group" aria-label="Quick filters">
        {(
          [
            ['urgent', 'Urgent'],
            ['high_priority', 'High priority'],
            ['handoff_required', 'Handoff'],
            ['waiting_for_payment', 'Waiting payment'],
            ['ready_to_order', 'Ready to order'],
            ['low_confidence', 'Low confidence'],
            ['assigned_to_me', 'Assigned to me'],
            ['unassigned', 'Unassigned'],
            ['needs_attention', 'Needs attention'],
          ] as const
        ).map(([key, label]) => {
          const active = Boolean(filters[key]);
          return (
            <button
              key={key}
              type="button"
              className={`filter-chip${active ? ' filter-chip--active' : ''}`}
              aria-pressed={active}
              onClick={() => {
                if (key === 'handoff_required') {
                  update({ handoff_required: active ? undefined : true });
                } else {
                  toggleFlag(key);
                }
              }}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
