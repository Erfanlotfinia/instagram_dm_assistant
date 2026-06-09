import { useEffect, useState } from 'react';

import { apiClient } from '../../services/apiClient';
import type { AgentDecisionTrace } from '../../types/conversation';
import { RiskBadge } from './RiskBadge';

export function DecisionTraceViewer({ shopId, conversationId }: { shopId: string; conversationId: string }) {
  const [traces, setTraces] = useState<AgentDecisionTrace[]>([]);
  const [selected, setSelected] = useState<AgentDecisionTrace | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!apiClient.listConversationDecisionTraces) { setTraces([]); return; }
    apiClient.listConversationDecisionTraces(shopId, conversationId)
      .then((rows) => { setTraces(rows); setSelected(rows[0] ?? null); })
      .catch((exc) => setError(exc instanceof Error ? exc.message : 'Failed to load decision traces'));
  }, [shopId, conversationId]);

  return (
    <section className="card" id="decision-trace">
      <h2>Decision trace</h2>
      <p className="muted">Business-level audit trail only; no private chain-of-thought is stored.</p>
      {error ? <div role="alert" className="alert alert--error">{error}</div> : null}
      {!traces.length ? <p>No decision traces yet.</p> : (
        <div className="split-panel">
          <ul className="trace-list" aria-label="Decision traces">
            {traces.map((trace) => (
              <li key={trace.id}>
                <button className="button button--ghost" type="button" onClick={() => setSelected(trace)}>
                  {new Date(trace.created_at).toLocaleString()} · {trace.intent ?? 'unknown'} <RiskBadge level={trace.risk_score?.risk_level} score={trace.risk_score?.score} />
                </button>
              </li>
            ))}
          </ul>
          {selected ? (
            <div>
              <h3>{selected.intent ?? 'Unknown intent'}</h3>
              <RiskBadge level={selected.risk_score?.risk_level} score={selected.risk_score?.score} />
              <dl className="detail-list">
                <dt>Next state</dt><dd>{selected.next_state}</dd>
                <dt>Auto-send</dt><dd>{selected.auto_send_allowed ? 'Allowed' : 'Blocked'}</dd>
                <dt>Handoff</dt><dd>{selected.human_handoff_required ? 'Required' : 'Not required'}</dd>
                <dt>Reasoning summary</dt><dd>{selected.reasoning_summary ?? '—'}</dd>
              </dl>
              <pre>{JSON.stringify({ extracted_slots: selected.extracted_slots, normalized_slots: selected.normalized_slots, product_candidates: selected.product_candidates, selected_product_id: selected.selected_product_id, variant_resolution: selected.variant_resolution, inventory_result: selected.inventory_result, risk_score: selected.risk_score, order_action: selected.order_action, outbound_message_id: selected.outbound_message_id }, null, 2)}</pre>
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
