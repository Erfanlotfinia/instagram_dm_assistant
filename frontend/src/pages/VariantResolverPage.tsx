import { FormEvent, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import {
  formatConfidence,
  formatMismatchReason,
  normalizeResolverResult,
  stockStatus,
  uniqueAlternatives,
} from '../lib/variantResolver';
import { apiClient } from '../services/apiClient';
import type { VariantAlternative, VariantResolverResult } from '../types/fashion';

const EXAMPLE_INPUTS = [
  { label: 'Persian black L', rawColor: 'مشکی', rawSize: 'L', quantity: 1 },
  { label: 'Persian black (no size)', rawColor: 'سیاه', rawSize: '', quantity: 1 },
  { label: 'English medium', rawColor: 'black', rawSize: 'M', quantity: 2 },
] as const;

function ConfidenceMeter({
  label,
  value,
  tone = 'default',
}: {
  label: string;
  value: number;
  tone?: 'default' | 'success' | 'warning';
}) {
  const percent = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className={`resolver-confidence resolver-confidence--${tone}`}>
      <div className="resolver-confidence__meta">
        <span>{label}</span>
        <strong>{percent}%</strong>
      </div>
      <div className="resolver-confidence__track" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label={`${label} confidence`}>
        <div className="resolver-confidence__fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

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
    <div className="match-panel resolver-alternatives">
      <h3>{title}</h3>
      {rows.length === 0 ? (
        <p className="empty-state">{emptyMessage}</p>
      ) : (
        <div className="table-wrap">
          <table className="data-table data-table--compact">
            <thead>
              <tr>
                <th scope="col">SKU</th>
                <th scope="col">Color</th>
                <th scope="col">Size</th>
                <th scope="col">Stock</th>
                <th scope="col">Why suggested</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const stock = stockStatus(row.available_stock);
                return (
                  <tr key={row.variant_id}>
                    <td>
                      <span className="resolver-alt-sku">{row.sku}</span>
                    </td>
                    <td>{row.normalized_color ?? row.color ?? '—'}</td>
                    <td>{row.normalized_size ?? row.size ?? '—'}</td>
                    <td>
                      <span className={`resolver-stock-badge resolver-stock-badge--${stock.tone}`}>
                        {row.available_stock} · {stock.label}
                      </span>
                    </td>
                    <td>{row.reason.replaceAll('_', ' ')}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ResolverResultPanel({
  result,
  rawColor,
  rawSize,
}: {
  result: VariantResolverResult;
  rawColor: string;
  rawSize: string;
}) {
  const normalized = normalizeResolverResult(result);
  const stock = stockStatus(normalized.available_stock);
  const mismatchReasons = normalized.mismatch_reasons ?? [];
  const alternatives = uniqueAlternatives(normalized.alternatives ?? [], normalized.available_alternatives ?? []);
  const showAlternatives = alternatives.length > 0;

  return (
    <section className="dashboard-card dashboard-card--wide resolver-result">
      <div className="section-header">
        <h2>Resolver result</h2>
        <span className={`priority-badge priority-badge--${normalized.matched ? 'low' : 'urgent'}`}>
          {normalized.matched ? 'Matched' : 'No match'}
        </span>
      </div>

      {normalized.matched ? (
        <div className="resolver-result__hero resolver-result__hero--matched">
          <div className="resolver-result__hero-main">
            <p className="resolver-result__eyebrow">Resolved variant</p>
            <p className="resolver-result__sku">{normalized.sku ?? 'Unknown SKU'}</p>
            <div className="resolver-result__chips">
              {normalized.normalized_color ? (
                <span className="resolver-chip">{normalized.normalized_color}</span>
              ) : null}
              {normalized.normalized_size ? (
                <span className="resolver-chip">{normalized.normalized_size}</span>
              ) : null}
            </div>
          </div>
          <div className="resolver-result__hero-side">
            <p className="resolver-result__stock-label">Available stock</p>
            <p className="resolver-result__stock-value">{normalized.available_stock ?? '—'}</p>
            <span className={`resolver-stock-badge resolver-stock-badge--${stock.tone}`}>{stock.label}</span>
          </div>
        </div>
      ) : (
        <div className="resolver-result__hero resolver-result__hero--unmatched">
          <div>
            <p className="resolver-result__eyebrow">Resolution failed</p>
            <p className="resolver-result__headline">No exact variant matched the request.</p>
            <p className="resolver-result__subcopy">
              Review normalization and mismatch reasons below, then try aliases or alternatives.
            </p>
          </div>
        </div>
      )}

      <div className="resolver-result__grid">
        <div className="match-panel resolver-normalization">
          <h3>Normalization</h3>
          <dl className="resolver-normalization__list">
            <div>
              <dt>Color input</dt>
              <dd dir="auto">{rawColor || '—'}</dd>
            </div>
            <div>
              <dt>Normalized color</dt>
              <dd>{normalized.normalized_color ?? '—'}</dd>
            </div>
            <div>
              <dt>Size input</dt>
              <dd>{rawSize || '—'}</dd>
            </div>
            <div>
              <dt>Normalized size</dt>
              <dd>{normalized.normalized_size ?? '—'}</dd>
            </div>
          </dl>
        </div>

        <div className="match-panel resolver-confidence-panel">
          <h3>Confidence</h3>
          <ConfidenceMeter label="Overall" value={normalized.confidence} tone={normalized.matched ? 'success' : 'warning'} />
          <ConfidenceMeter label="Color" value={normalized.color_confidence ?? 0} />
          <ConfidenceMeter label="Size" value={normalized.size_confidence ?? 0} />
        </div>
      </div>

      {mismatchReasons.length > 0 ? (
        <div className="match-panel resolver-mismatch">
          <h3>Mismatch reasons</h3>
          <div className="resolver-mismatch__chips">
            {mismatchReasons.map((reason) => (
              <span key={reason} className="resolver-mismatch-chip">
                {formatMismatchReason(reason)}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {showAlternatives ? (
        <AlternativeTable
          title="Suggested alternatives"
          rows={alternatives}
          emptyMessage="No alternative variants returned."
        />
      ) : null}

      <details className="match-panel resolver-raw-details">
        <summary>Technical details</summary>
        <dl className="detail-grid resolver-tech-details">
          {normalized.variant_id ? (
            <div>
              <dt>Variant ID</dt>
              <dd>
                <code>{normalized.variant_id}</code>
              </dd>
            </div>
          ) : null}
          <div>
            <dt>Overall confidence</dt>
            <dd>{formatConfidence(normalized.confidence)}</dd>
          </div>
        </dl>
        <pre className="resolver-raw-json">{JSON.stringify(normalized, null, 2)}</pre>
      </details>
    </section>
  );
}

export function VariantResolverPage() {
  const { selectedShopId, selectedShop } = useShop();
  const { showToast } = useToast();
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
    onSuccess: (data) => {
      const normalized = normalizeResolverResult(data);
      showToast(
        normalized.matched
          ? `Matched ${normalized.sku ?? 'variant'} with ${formatConfidence(normalized.confidence)} confidence.`
          : 'No exact variant match. Review mismatch reasons and alternatives.',
        normalized.matched ? 'success' : 'info',
      );
    },
    onError: (error) => {
      showToast(error instanceof Error ? error.message : 'Resolver request failed', 'error');
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!selectedShopId) {
      showToast('Select a shop before running the resolver.', 'error');
      return;
    }
    if (!productId) {
      showToast('Select a product to test.', 'error');
      return;
    }
    resolver.mutate();
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
  const products = Array.isArray(productsQuery.data) ? productsQuery.data : [];

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
                  {products.map((product) => (
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

        {productsQuery.isError ? (
          <div className="resolver-error-card">
            <p className="form-error">
              {productsQuery.error instanceof Error
                ? productsQuery.error.message
                : 'Failed to load products'}
            </p>
            <button
              className="button button--ghost-dark"
              type="button"
              onClick={() => void productsQuery.refetch()}
            >
              Retry loading products
            </button>
          </div>
        ) : null}

        {resolver.isError ? (
          <div className="resolver-error-card">
            <p className="form-error">
              {resolver.error instanceof Error ? resolver.error.message : 'Resolver request failed'}
            </p>
            <button
              className="button button--ghost-dark"
              type="button"
              onClick={() => resolver.mutate()}
              disabled={!canSubmit}
            >
              Retry resolver
            </button>
          </div>
        ) : null}
      </section>

      {resolver.isPending ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="loading-state">Running variant resolver…</p>
        </section>
      ) : null}

      {resolver.data ? (
        <ResolverResultPanel result={resolver.data} rawColor={rawColor} rawSize={rawSize} />
      ) : null}
    </div>
  );
}
