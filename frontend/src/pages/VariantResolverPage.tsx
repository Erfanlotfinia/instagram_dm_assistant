import { FormEvent, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { VariantAlternative, VariantResolverResult } from '../types/fashion';

const EXAMPLE_INPUTS = [
  { label: 'Persian black L', rawColor: 'مشکی', rawSize: 'L', quantity: 1 },
  { label: 'Persian black (no size)', rawColor: 'سیاه', rawSize: '', quantity: 1 },
  { label: 'English medium', rawColor: 'black', rawSize: 'M', quantity: 2 },
] as const;

function AlternativeTable({
  title,
  rows,
  emptyMessage,
}: {
  title: string;
  rows: VariantAlternative[];
  emptyMessage: string;
}) {
  return (
    <div className="match-panel">
      <h3>{title}</h3>
      {rows.length === 0 ? (
        <p className="empty-state">{emptyMessage}</p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Color</th>
                <th>Size</th>
                <th>Stock</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.variant_id}>
                  <td>{row.sku}</td>
                  <td>{row.normalized_color ?? row.color ?? '—'}</td>
                  <td>{row.normalized_size ?? row.size ?? '—'}</td>
                  <td>{row.available_stock}</td>
                  <td>{row.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ResolverResultPanel({ result }: { result: VariantResolverResult }) {
  return (
    <section className="dashboard-card dashboard-card--wide">
      <div className="section-header">
        <h2>Resolver result</h2>
        <span className={`priority-badge priority-badge--${result.matched ? 'low' : 'urgent'}`}>
          {result.matched ? 'Matched' : 'No match'}
        </span>
      </div>

      <div className="stats-grid">
        <article className={`stat-card${result.matched ? '' : ' stat-card--warning'}`}>
          <p className="stat-card__label">Confidence</p>
          <p className="stat-card__value">{Math.round(result.confidence * 100)}%</p>
        </article>
        <article className="stat-card">
          <p className="stat-card__label">Available stock</p>
          <p className="stat-card__value">{result.available_stock ?? '—'}</p>
        </article>
        <article className="stat-card">
          <p className="stat-card__label">Alternatives</p>
          <p className="stat-card__value">{result.alternatives.length}</p>
        </article>
        <article className="stat-card">
          <p className="stat-card__label">In-stock alternatives</p>
          <p className="stat-card__value">{result.available_alternatives.length}</p>
        </article>
      </div>

      {result.matched ? (
        <dl className="detail-grid">
          <div>
            <dt>Variant ID</dt>
            <dd>{result.variant_id ?? '—'}</dd>
          </div>
          <div>
            <dt>SKU</dt>
            <dd>{result.sku ?? '—'}</dd>
          </div>
          <div>
            <dt>Normalized color</dt>
            <dd>{result.normalized_color ?? '—'}</dd>
          </div>
          <div>
            <dt>Normalized size</dt>
            <dd>{result.normalized_size ?? '—'}</dd>
          </div>
        </dl>
      ) : null}

      {result.mismatch_reasons.length > 0 ? (
        <div className="match-panel">
          <h3>Mismatch reasons</h3>
          <ul className="timeline-list">
            {result.mismatch_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <AlternativeTable
        title="Suggested alternatives"
        rows={result.alternatives}
        emptyMessage="No alternative variants returned."
      />
      <AlternativeTable
        title="In-stock alternatives"
        rows={result.available_alternatives}
        emptyMessage="No in-stock alternatives available."
      />

      <details className="match-panel resolver-raw-details">
        <summary>Raw JSON response</summary>
        <pre className="resolver-raw-json">{JSON.stringify(result, null, 2)}</pre>
      </details>
    </section>
  );
}

export function VariantResolverPage() {
  const { selectedShopId, selectedShop } = useShop();
  const [productId, setProductId] = useState('');
  const [rawColor, setRawColor] = useState('');
  const [rawSize, setRawSize] = useState('');
  const [quantity, setQuantity] = useState(1);

  const productsQuery = useQuery({
    queryKey: queryKeys.products(selectedShopId),
    queryFn: () => apiClient.listProducts(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const resolver = useMutation({
    mutationFn: () =>
      apiClient.testVariantResolver(selectedShopId, {
        product_id: productId,
        raw_color: rawColor || undefined,
        raw_size: rawSize || undefined,
        quantity,
      }),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (selectedShopId && productId) {
      resolver.mutate();
    }
  }

  function applyExample(example: (typeof EXAMPLE_INPUTS)[number]) {
    setRawColor(example.rawColor);
    setRawSize(example.rawSize);
    setQuantity(example.quantity);
  }

  function resetForm() {
    setProductId('');
    setRawColor('');
    setRawSize('');
    setQuantity(1);
    resolver.reset();
  }

  const canSubmit = Boolean(selectedShopId && productId && !resolver.isPending);

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Sprint A tooling</p>
        <h1>Variant resolver test</h1>
        <p>
          Test backend-only normalization, variant matching, stock checks, and alternatives without
          calling the LLM.
        </p>
        <ShopSelector />
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Test input</h2>
        <p className="analytics-toolbar__summary">
          Pick a product, enter raw customer color/size text, then run the resolver against{' '}
          {selectedShop?.name ?? 'the selected shop'}.
        </p>

        {!selectedShopId ? (
          <p className="empty-state">Select a shop before running the resolver.</p>
        ) : (
          <form className="variant-resolver-form" onSubmit={submit}>
            <div className="filter-grid">
              <label className="form-field form-field--wide">
                <span>Product</span>
                <select
                  value={productId}
                  onChange={(event) => setProductId(event.target.value)}
                  required
                  disabled={productsQuery.isLoading}
                >
                  <option value="">
                    {productsQuery.isLoading ? 'Loading products…' : 'Select a product'}
                  </option>
                  {productsQuery.data?.map((product) => (
                    <option key={product.id} value={product.id}>
                      {product.title}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                <span>Raw color</span>
                <input
                  value={rawColor}
                  onChange={(event) => setRawColor(event.target.value)}
                  placeholder="مشکی"
                  dir="auto"
                />
              </label>

              <label className="form-field">
                <span>Raw size</span>
                <input
                  value={rawSize}
                  onChange={(event) => setRawSize(event.target.value)}
                  placeholder="L"
                />
              </label>

              <label className="form-field">
                <span>Quantity</span>
                <input
                  type="number"
                  min={1}
                  value={quantity}
                  onChange={(event) => setQuantity(Number(event.target.value) || 1)}
                />
              </label>
            </div>

            <div className="form-field variant-resolver-form__examples">
              <span>Example inputs</span>
              <div className="filter-chips" role="group" aria-label="Example resolver inputs">
                {EXAMPLE_INPUTS.map((example) => (
                  <button
                    key={example.label}
                    type="button"
                    className="filter-chip"
                    onClick={() => applyExample(example)}
                  >
                    {example.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="button-row">
              <button className="button button--primary" type="submit" disabled={!canSubmit}>
                {resolver.isPending ? 'Running resolver…' : 'Run resolver'}
              </button>
              <button className="button button--ghost-dark" type="button" onClick={resetForm}>
                Reset
              </button>
            </div>
          </form>
        )}

        {productsQuery.error ? (
          <p className="form-error">
            {productsQuery.error instanceof Error
              ? productsQuery.error.message
              : 'Failed to load products'}
          </p>
        ) : null}

        {resolver.error ? (
          <p className="form-error">
            {resolver.error instanceof Error ? resolver.error.message : 'Resolver request failed'}
          </p>
        ) : null}
      </section>

      {resolver.data ? <ResolverResultPanel result={resolver.data} /> : null}
    </div>
  );
}
