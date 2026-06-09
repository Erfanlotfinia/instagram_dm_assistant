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
    <section className="match-panel">
      <h3>{title}</h3>
      <ul className="checklist">
        {events.map((event) => (
          <li key={event.id}>
            <strong>{event.event_type}</strong>
            <pre className="resolver-raw-json">{JSON.stringify(event.payload_json, null, 2)}</pre>
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
    <aside className="trace-drawer" aria-label="Decision trace drawer">
      <div className="trace-drawer__header">
        <h2>Decision trace</h2>
        <button className="button button--ghost-dark" type="button" onClick={onClose}>
          Close
        </button>
      </div>
      {loading ? <p className="loading-state">Loading trace…</p> : null}
      {!loading && !trace ? <p className="empty-state">No trace selected.</p> : null}
      {trace ? (
        <div className="trace-drawer__body">
          <dl className="detail-grid">
            <div>
              <dt>Trace ID</dt>
              <dd>{trace.trace_id}</dd>
            </div>
            <div>
              <dt>Intent</dt>
              <dd>{String(trace.header.intent ?? '—')}</dd>
            </div>
            <div>
              <dt>Next state</dt>
              <dd>{String(trace.header.next_state ?? '—')}</dd>
            </div>
            <div>
              <dt>Auto-send allowed</dt>
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
    </aside>
  );
}
