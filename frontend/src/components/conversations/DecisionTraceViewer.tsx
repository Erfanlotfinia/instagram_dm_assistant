import { useEffect, useState } from 'react';

import { EmptyState, LoadingState } from '../data';
import { Badge, type BadgeTone } from '../ui';
import { cn } from '../../lib/cn';
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

function traceOutcome(trace: AgentDecisionTrace): { label: string; tone: BadgeTone } {
  if (trace.human_handoff_required) return { label: 'Handoff', tone: 'danger' };
  if (trace.auto_send_allowed) return { label: 'Automated', tone: 'success' };
  return { label: 'LLM', tone: 'warning' };
}

function StatusFact({ label, value, tone }: { label: string; value: string; tone: FactTone }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</dt>
      <dd>
        <Badge tone={tone}>{value}</Badge>
      </dd>
    </div>
  );
}

function TraceSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2 border-t border-border pt-3 first:border-0 first:pt-0">
      <h4 className="text-[11px] font-semibold uppercase tracking-wide text-muted">{title}</h4>
      {children}
    </section>
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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!apiClient.listConversationDecisionTraces) {
      setTraces([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    apiClient
      .listConversationDecisionTraces(shopId, conversationId)
      .then((rows) => {
        setTraces(rows);
        setSelectedId(rows[0]?.id ?? null);
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : 'Failed to load decision traces'))
      .finally(() => setLoading(false));
  }, [shopId, conversationId]);

  const selected = traces.find((trace) => trace.id === selectedId) ?? null;

  return (
    <section id="decision-trace" aria-label="Decision trace" className="flex flex-col gap-3">
      <header className="flex flex-col gap-1">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-fg">Decision trace</h2>
          {traces.length > 0 ? (
            <Badge tone="neutral">{traces.length}</Badge>
          ) : null}
        </div>
        <p className="text-xs leading-relaxed text-subtle">
          Business-level audit trail only; no private chain-of-thought is stored.
        </p>
      </header>

      {loading ? <LoadingState label="Loading traces…" /> : null}

      {error ? (
        <div role="alert" className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
          {error}
        </div>
      ) : null}

      {!loading && !traces.length && !error ? (
        <EmptyState title="No decision traces yet" className="py-8" />
      ) : null}

      {traces.length ? (
        <div className="flex min-h-0 flex-col gap-3">
          <ul className="flex max-h-36 flex-col gap-1.5 overflow-y-auto" aria-label="Decision traces">
            {traces.map((trace) => {
              const active = trace.id === selectedId;
              const outcome = traceOutcome(trace);
              return (
                <li key={trace.id}>
                  <button
                    type="button"
                    aria-current={active ? 'true' : undefined}
                    onClick={() => setSelectedId(trace.id)}
                    className={cn(
                      'w-full rounded-lg border px-3 py-2 text-left transition-colors',
                      active
                        ? 'border-accent/40 bg-accent-soft'
                        : 'border-border bg-surface-sunken hover:border-border hover:bg-surface-raised',
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="truncate text-sm font-medium text-fg">
                        {humanize(trace.intent ?? 'unknown')}
                      </span>
                      <Badge tone={outcome.tone} dot>
                        {outcome.label}
                      </Badge>
                    </div>
                    <time className="mt-1 block text-[11px] tabular-nums text-subtle" dateTime={trace.created_at}>
                      {formatTraceTime(trace.created_at)}
                    </time>
                  </button>
                </li>
              );
            })}
          </ul>

          {selected ? (
            <div className="flex flex-col gap-3 rounded-lg border border-border bg-surface-sunken p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-fg">{humanize(selected.intent ?? 'Unknown intent')}</h3>
                <RiskBadge level={selected.risk_score?.risk_level} score={selected.risk_score?.score} />
              </div>

              <dl className="grid grid-cols-2 gap-3">
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

              <TraceSection title="Reasoning summary">
                <p className="text-sm leading-relaxed text-fg">{selected.reasoning_summary ?? '—'}</p>
              </TraceSection>

              <details className="group rounded-lg border border-border bg-surface overflow-hidden">
                <summary className="cursor-pointer select-none px-3 py-2 text-xs font-medium text-muted transition-colors hover:text-fg">
                  Raw trace payload
                </summary>
                <pre className="max-h-40 overflow-auto border-t border-border bg-surface-sunken p-3 text-[11px] leading-relaxed text-muted">
                  {JSON.stringify(buildRawPayload(selected), null, 2)}
                </pre>
              </details>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
