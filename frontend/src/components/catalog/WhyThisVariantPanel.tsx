import { Badge } from '../ui';
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
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-surface-sunken p-4">
      <h3 className="text-sm font-semibold text-fg">Why this variant?</h3>
      <p className="text-sm leading-relaxed text-muted">{top.rationale}</p>
      {top.rules_fired.length > 0 ? (
        <div className="flex flex-col gap-1.5">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted">Rules fired</span>
          <span className="flex flex-wrap gap-1.5">
            {top.rules_fired.map((rule) => (
              <Badge key={rule} tone="accent">
                {rule}
              </Badge>
            ))}
          </span>
        </div>
      ) : null}
      {top.matched_aliases.length > 0 ? (
        <div className="flex flex-col gap-1.5">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted">Matched aliases</span>
          <span className="flex flex-wrap gap-1.5">
            {top.matched_aliases.map((alias) => (
              <Badge key={alias} tone="neutral">
                {alias}
              </Badge>
            ))}
          </span>
        </div>
      ) : null}
      {trace?.qdrant_query_metadata && Object.keys(trace.qdrant_query_metadata).length > 0 ? (
        <details className="rounded-lg border border-border bg-surface p-3">
          <summary className="cursor-pointer text-sm font-medium text-fg">Retrieval metadata</summary>
          <pre className="mt-2 overflow-x-auto text-xs text-subtle">
            {JSON.stringify(trace.qdrant_query_metadata, null, 2)}
          </pre>
        </details>
      ) : null}
    </div>
  );
}
