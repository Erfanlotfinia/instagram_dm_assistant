import type { ResolveVariantResponse, ResolverTrace } from '../../types/resolve';

export function WhyThisVariantPanel({
  result,
  trace,
}: {
  result: ResolveVariantResponse;
  trace: ResolverTrace | null;
}) {
  const top = result.candidates[0];
  if (!top) return null;
  return (
    <div className="cc-why">
      <h3 className="cc-subhead">Why this variant?</h3>
      <p className="cc-why__rationale">{top.rationale}</p>
      {top.rules_fired.length > 0 ? (
        <div className="cc-why__row">
          <span className="cc-why__key">Rules fired</span>
          <span className="cc-why__tags">
            {top.rules_fired.map((rule) => (
              <span key={rule} className="cc-tag cc-tag--rule">
                {rule}
              </span>
            ))}
          </span>
        </div>
      ) : null}
      {top.matched_aliases.length > 0 ? (
        <div className="cc-why__row">
          <span className="cc-why__key">Matched aliases</span>
          <span className="cc-why__tags">
            {top.matched_aliases.map((alias) => (
              <span key={alias} className="cc-tag">
                {alias}
              </span>
            ))}
          </span>
        </div>
      ) : null}
      {trace?.qdrant_query_metadata && Object.keys(trace.qdrant_query_metadata).length > 0 ? (
        <details className="cc-why__meta">
          <summary>Retrieval metadata</summary>
          <pre className="cc-json">{JSON.stringify(trace.qdrant_query_metadata, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}
