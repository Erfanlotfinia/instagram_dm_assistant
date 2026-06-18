import { useEffect, useState } from 'react';

import { EmptyState } from '../data';
import { Badge, type BadgeTone } from '../ui';
import { apiClient } from '../../services/apiClient';
import type { AgentDecisionTrace } from '../../types/conversation';
import { RiskBadge } from './RiskBadge';

type FactTone = BadgeTone;

function formatTraceTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function humanize(value: string): string {
  return value.replace(/_/g, ' ');
}

function StatusFact({ label, value, tone }: { label: string; value: string; tone: FactTone }) {
  return (
    <div className="context-facts__item">
      <dt>{label}</dt>
      <dd>
        <Badge tone={tone}>{value}</Badge>
      </dd>
    </div>
  );
}

function buildRawPayload(trace: AgentDecisionTrace) {
  return {
    extracted_slots: trace.extracted_slots,
    normalized_slots: trace.normalized_slots,
    product_candidates: trace.product_candidates,
    selected_product_id: trace.selected_product_id,
    variant_resolution: trace.variant_resolution,
    inventory_result: trace.inventory_result,
    risk_score: trace.risk_score,
    order_action: trace.order_action,
    outbound_message_id: trace.outbound_message_id,
  };
}

export function DecisionTraceViewer({
  shopId,
  conversationId,
}: {
  shopId: string;
  conversationId: string;
}) {
  const [traces, setTraces] = useState<AgentDecisionTrace[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!apiClient.listConversationDecisionTraces) {
      setTraces([]);
      return;
    }
    apiClient
      .listConversationDecisionTraces(shopId, conversationId)
      .then((rows) => {
        setTraces(rows);
        setSelectedId(rows[0]?.id ?? null);
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : 'Failed to load decision traces'));
  }, [shopId, conversationId]);

  const selected = traces.find((trace) => trace.id === selectedId) ?? null;

  return (
    <section className="decision-trace" id="decision-trace" aria-label="Decision trace">
      <header className="decision-trace__header">
        <h2 className="decision-trace__title">Decision trace</h2>
        <p className="decision-trace__note">
          Business-level audit trail only; no private chain-of-thought is stored.
        </p>
      </header>

      {error ? (
        <div role="alert" className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
          {error}
        </div>
      ) : null}

      {!traces.length && !error ? <EmptyState title="No decision traces yet" /> : null}

      {traces.length ? (
        <div className="decision-trace__layout">
          <ul className="decision-trace__list" aria-label="Decision traces">
            {traces.map((trace) => {
              const active = trace.id === selectedId;
              return (
                <li key={trace.id}>
                  <button
                    type="button"
                    className={`decision-trace__item${active ? ' decision-trace__item--active' : ''}`}
                    aria-current={active}
                    onClick={() => setSelectedId(trace.id)}
                  >
                    <span className="decision-trace__item-top">
                      <span className="decision-trace__item-intent">{trace.intent ?? 'unknown'}</span>
                      <RiskBadge level={trace.risk_score?.risk_level} score={trace.risk_score?.score} />
                    </span>
                    <time className="decision-trace__item-time" dateTime={trace.created_at}>
                      {formatTraceTime(trace.created_at)}
                    </time>
                  </button>
                </li>
              );
            })}
          </ul>

          {selected ? (
            <div className="decision-trace__detail">
              <div className="decision-trace__detail-head">
                <h3 className="decision-trace__detail-title">{selected.intent ?? 'Unknown intent'}</h3>
                <RiskBadge level={selected.risk_score?.risk_level} score={selected.risk_score?.score} />
              </div>

              <dl className="context-facts">
                <StatusFact label="Next state" value={humanize(selected.next_state)} tone="neutral" />
                <StatusFact
                  label="Auto-send"
                  value={selected.auto_send_allowed ? 'Allowed' : 'Blocked'}
                  tone={selected.auto_send_allowed ? 'success' : 'warning'}
                />
                <StatusFact
                  label="Handoff"
                  value={selected.human_handoff_required ? 'Required' : 'Not required'}
                  tone={selected.human_handoff_required ? 'warning' : 'success'}
                />
              </dl>

              <div className="decision-trace__reasoning">
                <h4 className="context-section__title">Reasoning summary</h4>
                <p className="context-section__body">{selected.reasoning_summary ?? '—'}</p>
              </div>

              <details className="decision-trace__raw">
                <summary>Raw trace payload</summary>
                <pre>{JSON.stringify(buildRawPayload(selected), null, 2)}</pre>
              </details>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
