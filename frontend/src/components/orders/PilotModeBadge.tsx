import type { PilotModeSnapshot } from '../../types/order';

interface PilotModeBadgeProps {
  snapshot: PilotModeSnapshot | null | undefined;
}

export function PilotModeBadge({ snapshot }: PilotModeBadgeProps) {
  if (!snapshot) {
    return null;
  }

  if (snapshot.emergency_stop) {
    return <span className="priority-badge priority-badge--urgent">Pilot: Emergency stop</span>;
  }

  if (snapshot.pilot_enabled) {
    return (
      <span className="priority-badge priority-badge--medium">
        Pilot: {snapshot.pilot_name ?? 'Active'}
      </span>
    );
  }

  if (snapshot.require_operator_approval) {
    return <span className="priority-badge priority-badge--high">Operator approval required</span>;
  }

  return <span className="priority-badge priority-badge--low">Pilot idle</span>;
}
