import { Button } from '../ui';
import { EmptyState, LoadingState } from '../data';
import type { AssembledDecisionTrace } from '../../types/trust';

type DecisionTraceDrawerProps = {
  open: boolean;
  trace: AssembledDecisionTrace | null;
  loading?: boolean;
  onClose: () => void;
};

function EventList({ title, events }: { title: string; events: AssembledDecisionTrace['policy_checks'] }) {
  if (!events.length) {
    return null;
  }
  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-fg">{title}</h3>
      <ul className="space-y-2">
        {events.map((event) => (
          <li key={event.id} className="rounded-lg border border-border bg-surface-sunken p-3">
            <strong className="text-sm text-fg">{event.event_type}</strong>
            <pre className="mt-2 overflow-x-auto text-xs text-subtle">{JSON.stringify(event.payload_json, null, 2)}</pre>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function DecisionTraceDrawer({ open, trace, loading, onClose }: DecisionTraceDrawerProps) {
  if (!open) {
    return null;
  }

  return (
    <aside
      className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l border-border bg-surface shadow-xl"
      aria-label="Decision trace drawer"
    >
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-fg">Decision trace</h2>
        <Button type="button" variant="ghost" size="sm" onClick={onClose}>
          Close
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? <LoadingState label="Loading trace…" /> : null}
        {!loading && !trace ? <EmptyState title="No trace selected" /> : null}
        {trace ? (
          <div className="flex flex-col gap-4">
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-xs text-muted">Trace ID</dt>
                <dd className="font-mono text-xs">{trace.trace_id}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Intent</dt>
                <dd>{String(trace.header.intent ?? '—')}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Next state</dt>
                <dd>{String(trace.header.next_state ?? '—')}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Auto-send allowed</dt>
                <dd>{trace.header.auto_send_allowed ? 'Yes' : 'No'}</dd>
              </div>
            </dl>
            <EventList title="Retrieval evidence" events={trace.retrieval_evidence} />
            <EventList title="Slots extracted" events={trace.slots_extracted} />
            <EventList title="Confidence bands" events={trace.confidence_bands} />
            <EventList title="Policy checks" events={trace.policy_checks} />
            <EventList title="Actions attempted" events={trace.actions_attempted} />
            <EventList title="Actions blocked" events={trace.actions_blocked} />
          </div>
        ) : null}
      </div>
    </aside>
  );
}
