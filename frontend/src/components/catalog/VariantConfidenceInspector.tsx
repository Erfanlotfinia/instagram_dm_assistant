import type { ResolveVariantResponse } from '../../types/resolve';

export function VariantConfidenceInspector({ result }: { result: ResolveVariantResponse }) {
  return (
    <div className="cc-inspector">
      <div className="cc-inspector__head">
        <h3 className="cc-subhead">Variant candidates</h3>
        <span className={`status-pill status-pill--${result.confidence_band}`}>
          {result.confidence_band} · {Math.round(result.confidence_score * 100)}%
        </span>
      </div>
      {result.missing_slots.length > 0 ? (
        <p className="cc-missing-slots">Missing slots: {result.missing_slots.join(', ')}</p>
      ) : null}
      {result.candidates.length === 0 ? (
        <p className="empty-state cc-state">No variant candidates.</p>
      ) : (
        <div className="table-wrap">
          <table className="data-table data-table--compact cc-variant-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Color / Size</th>
                <th>Match</th>
                <th>Stock</th>
              </tr>
            </thead>
            <tbody>
              {result.candidates.map((candidate) => (
                <tr key={candidate.variant_id}>
                  <td className="cc-variant-table__sku">{candidate.sku}</td>
                  <td>
                    {candidate.color ?? '—'} / {candidate.size ?? '—'}
                  </td>
                  <td>
                    <span className={`status-pill status-pill--${candidate.confidence_band}`}>
                      {Math.round(candidate.score * 100)}%
                    </span>
                  </td>
                  <td className={candidate.available_stock > 0 ? 'cc-stock-ok' : 'cc-stock-out'}>
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
