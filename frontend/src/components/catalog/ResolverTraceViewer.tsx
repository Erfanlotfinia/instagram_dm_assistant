import type { ResolverTrace } from '../../types/resolve';

export function ResolverTraceViewer({ trace }: { trace: ResolverTrace }) {
  return (
    <div className="cc-trace">
      <div className="cc-card__head">
        <div>
          <h2 className="cc-card__title">Resolver trace</h2>
          <p className="cc-card__hint cc-trace__id">{trace.id}</p>
        </div>
        <span className={`status-pill status-pill--${trace.confidence_band}`}>
          {trace.confidence_band} · {Math.round(trace.confidence_score * 100)}%
        </span>
      </div>

      <div className="cc-trace__meta">
        <div className="cc-trace__metaitem">
          <span className="cc-trace__metakey">Type</span>
          <span className="cc-trace__metaval">{trace.trace_type}</span>
        </div>
        <div className="cc-trace__metaitem">
          <span className="cc-trace__metakey">Missing slots</span>
          <span className="cc-trace__metaval">
            {trace.missing_slots.length > 0 ? trace.missing_slots.join(', ') : 'None'}
          </span>
        </div>
      </div>

      {trace.rationale ? <p className="cc-trace__rationale">{trace.rationale}</p> : null}

      {trace.rules_fired.length > 0 ? (
        <div className="cc-why__row">
          <span className="cc-why__key">Rules fired</span>
          <span className="cc-why__tags">
            {trace.rules_fired.map((rule) => (
              <span key={rule} className="cc-tag cc-tag--rule">
                {rule}
              </span>
            ))}
          </span>
        </div>
      ) : null}

      <details className="cc-why__meta" open>
        <summary>Top candidates ({trace.top_candidates.length})</summary>
        <pre className="cc-json">{JSON.stringify(trace.top_candidates, null, 2)}</pre>
      </details>
      <details className="cc-why__meta">
        <summary>Matched aliases ({trace.matched_aliases.length})</summary>
        <pre className="cc-json">{JSON.stringify(trace.matched_aliases, null, 2)}</pre>
      </details>
    </div>
  );
}
