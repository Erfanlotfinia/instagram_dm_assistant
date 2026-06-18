import { Badge } from '../ui';
import { EmptyState } from '../data';
import { confidenceBandTone } from '../../lib/confidenceBand';
import type { ResolveVariantResponse } from '../../types/resolve';

export function VariantConfidenceInspector({ result }: { result: ResolveVariantResponse }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-fg">Variant candidates</h3>
        <Badge tone={confidenceBandTone(result.confidence_band)}>
          {result.confidence_band} · {Math.round(result.confidence_score * 100)}%
        </Badge>
      </div>
      {result.missing_slots.length > 0 ? (
        <p className="text-sm text-warning">Missing slots: {result.missing_slots.join(', ')}</p>
      ) : null}
      {result.candidates.length === 0 ? (
        <EmptyState title="No variant candidates" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-subtle">
                <th className="px-3 py-2">SKU</th>
                <th className="px-3 py-2">Color / Size</th>
                <th className="px-3 py-2">Match</th>
                <th className="px-3 py-2">Stock</th>
              </tr>
            </thead>
            <tbody>
              {result.candidates.map((candidate) => (
                <tr key={candidate.variant_id} className="border-b border-border/70 last:border-0">
                  <td className="px-3 py-2 font-mono text-xs">{candidate.sku}</td>
                  <td className="px-3 py-2">
                    {candidate.color ?? '—'} / {candidate.size ?? '—'}
                  </td>
                  <td className="px-3 py-2">
                    <Badge tone={confidenceBandTone(candidate.confidence_band)}>
                      {Math.round(candidate.score * 100)}%
                    </Badge>
                  </td>
                  <td className={candidate.available_stock > 0 ? 'px-3 py-2 text-success' : 'px-3 py-2 text-danger'}>
                    {candidate.available_stock}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
