import { Badge } from '../ui';
import { confidenceBandTone } from '../../lib/confidenceBand';
import type { ResolverTrace } from '../../types/resolve';

export function ResolverTraceViewer({ trace }: { trace: ResolverTrace }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-fg">Resolver trace</h2>
          <p className="font-mono text-xs text-subtle">{trace.id}</p>
        </div>
        <Badge tone={confidenceBandTone(trace.confidence_band)}>
          {trace.confidence_band} · {Math.round(trace.confidence_score * 100)}%
        </Badge>
      </div>

      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs text-muted">Type</dt>
          <dd className="text-fg">{trace.trace_type}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Missing slots</dt>
          <dd className="text-fg">{trace.missing_slots.length > 0 ? trace.missing_slots.join(', ') : 'None'}</dd>
        </div>
      </dl>

      {trace.rationale ? <p className="text-sm leading-relaxed text-muted">{trace.rationale}</p> : null}

      {trace.rules_fired.length > 0 ? (
        <div className="flex flex-col gap-1.5 text-sm">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted">Rules fired</span>
          <span className="flex flex-wrap gap-1.5">
            {trace.rules_fired.map((rule) => (
              <Badge key={rule} tone="accent">
                {rule}
              </Badge>
            ))}
          </span>
        </div>
      ) : null}

      <details className="rounded-lg border border-border bg-surface-sunken p-3" open>
        <summary className="cursor-pointer text-sm font-medium text-fg">
          Top candidates ({trace.top_candidates.length})
        </summary>
        <pre className="mt-2 overflow-x-auto text-xs text-subtle">{JSON.stringify(trace.top_candidates, null, 2)}</pre>
      </details>
      <details className="rounded-lg border border-border bg-surface-sunken p-3">
        <summary className="cursor-pointer text-sm font-medium text-fg">
          Matched aliases ({trace.matched_aliases.length})
        </summary>
        <pre className="mt-2 overflow-x-auto text-xs text-subtle">{JSON.stringify(trace.matched_aliases, null, 2)}</pre>
      </details>
    </div>
  );
}
