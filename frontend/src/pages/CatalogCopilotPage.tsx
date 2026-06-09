import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { AliasEditor } from '../components/catalog/AliasEditor';
import { OperatorCorrectionPanel } from '../components/catalog/OperatorCorrectionPanel';
import { ResolverTraceViewer } from '../components/catalog/ResolverTraceViewer';
import { VariantConfidenceInspector } from '../components/catalog/VariantConfidenceInspector';
import { WhyThisVariantPanel } from '../components/catalog/WhyThisVariantPanel';
import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { ProductNormalized } from '../types/catalog';
import type { ProductCandidate, ResolveProductResponse, ResolveVariantResponse, ResolverTrace } from '../types/resolve';

const EXAMPLE_MESSAGES = [
  { label: 'Persian · black M', text: 'مشکی سایز M' },
  { label: 'Red blouse L', text: 'red blouse size L' },
  { label: 'Navy XL', text: 'سرمه ای xl' },
] as const;

const PAGE_SIZE = 10;

function formatApiError(error: unknown): string {
  return error instanceof Error ? error.message : 'Request failed';
}

function ScoreBar({ value, band }: { value: number; band: string }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className="cc-scorebar" role="img" aria-label={`${pct}% match`}>
      <div className={`cc-scorebar__fill cc-scorebar__fill--${band}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function CatalogCopilotPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(1);
  const [messageText, setMessageText] = useState('مشکی سایز M');
  const [selectedProduct, setSelectedProduct] = useState<ProductNormalized | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [productResult, setProductResult] = useState<ResolveProductResponse | null>(null);
  const [variantResult, setVariantResult] = useState<ResolveVariantResponse | null>(null);
  const [activeTrace, setActiveTrace] = useState<ResolverTrace | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(searchInput.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    setPage(1);
    setSelectedProduct(null);
    setSelectedCandidateId(null);
    setProductResult(null);
    setVariantResult(null);
    setActiveTrace(null);
  }, [selectedShopId]);

  const catalogQuery = useQuery({
    queryKey: queryKeys.catalogProducts(selectedShopId, debouncedSearch, page),
    queryFn: () =>
      apiClient.listCatalogProducts(selectedShopId!, {
        search: debouncedSearch || undefined,
        page,
        page_size: PAGE_SIZE,
      }),
    enabled: Boolean(selectedShopId),
  });

  const indexedCount = useMemo(
    () => catalogQuery.data?.items.filter((item) => item.last_indexed_at).length ?? 0,
    [catalogQuery.data?.items],
  );

  const reindexMutation = useMutation({
    mutationFn: () => apiClient.reindexCatalog(selectedShopId!),
    onSuccess: (result) => {
      showToast(`Reindexed ${result.indexed_products}/${result.total_products} products`, 'success');
      void queryClient.invalidateQueries({ queryKey: queryKeys.catalogProducts(selectedShopId) });
    },
    onError: (error) => showToast(formatApiError(error), 'error'),
  });

  const resolveMutation = useMutation({
    mutationFn: async () => {
      if (!selectedShopId) {
        throw new Error('Select a shop first');
      }

      const productResponse = await apiClient.resolveProduct(selectedShopId, {
        message_text: messageText,
        limit: 5,
      });

      const productId =
        selectedProduct?.product_id ??
        selectedCandidateId ??
        productResponse.candidates[0]?.product_id;

      const variantResponse = await apiClient.resolveVariant(selectedShopId, {
        message_text: messageText,
        product_id: productId,
        limit: 5,
      });

      const trace = await apiClient.getResolverTrace(selectedShopId, variantResponse.trace_id);
      return { productResponse, variantResponse, trace };
    },
    onSuccess: ({ productResponse, variantResponse, trace }) => {
      setProductResult(productResponse);
      setVariantResult(variantResponse);
      setActiveTrace(trace);
      if (productResponse.candidates[0] && !selectedCandidateId) {
        setSelectedCandidateId(productResponse.candidates[0].product_id);
      }
    },
    onError: (error) => showToast(formatApiError(error), 'error'),
  });

  function handleResolveSubmit(event: FormEvent) {
    event.preventDefault();
    if (!selectedShopId || !messageText.trim()) {
      showToast('Enter a customer message to resolve', 'error');
      return;
    }
    resolveMutation.mutate();
  }

  function handleSelectCandidate(candidate: ProductCandidate) {
    setSelectedCandidateId(candidate.product_id);
  }

  const totalPages = catalogQuery.data
    ? Math.max(1, Math.ceil(catalogQuery.data.total / catalogQuery.data.page_size))
    : 1;
  const isResolving = resolveMutation.isPending;
  const items = catalogQuery.data?.items ?? [];
  const hasResults = Boolean(productResult || variantResult);

  return (
    <div className="page-stack catalog-copilot">
      <header className="cc-hero">
        <div className="cc-hero__top">
          <div className="cc-hero__intro">
            <span className="cc-hero__eyebrow">Catalog intelligence</span>
            <h1 className="cc-hero__title">Catalog Copilot</h1>
            <p className="cc-hero__subtitle">
              Normalize catalog entries, run hybrid retrieval, and resolve messy customer DMs to the right product and
              variant — with full trace visibility and operator review.
            </p>
          </div>
          <div className="cc-hero__controls">
            <div className="cc-hero__shop">
              <ShopSelector label="Active shop" />
            </div>
            <div className="cc-hero__actions">
              <button
                className="button button--primary"
                type="button"
                disabled={!selectedShopId || reindexMutation.isPending}
                onClick={() => reindexMutation.mutate()}
              >
                {reindexMutation.isPending ? 'Reindexing…' : 'Reindex catalog'}
              </button>
              <button
                className="button cc-hero__refresh"
                type="button"
                disabled={!selectedShopId || catalogQuery.isFetching}
                onClick={() => void catalogQuery.refetch()}
              >
                {catalogQuery.isFetching ? 'Refreshing…' : 'Refresh'}
              </button>
            </div>
          </div>
        </div>

        {selectedShopId ? (
          <div className="cc-stats">
            <div className="cc-stat">
              <span className="cc-stat__label">Normalized products</span>
              <span className="cc-stat__value">{catalogQuery.data?.total ?? '—'}</span>
            </div>
            <div className="cc-stat">
              <span className="cc-stat__label">Indexed on page</span>
              <span className="cc-stat__value">
                {catalogQuery.isLoading ? '…' : `${indexedCount}/${items.length}`}
              </span>
            </div>
            <div className="cc-stat">
              <span className="cc-stat__label">Product candidates</span>
              <span className="cc-stat__value">{productResult?.candidates.length ?? '—'}</span>
            </div>
            <div className="cc-stat">
              <span className="cc-stat__label">Last confidence</span>
              <span className="cc-stat__value">
                {activeTrace ? (
                  <span className={`status-pill status-pill--${activeTrace.confidence_band}`}>
                    {activeTrace.confidence_band}
                  </span>
                ) : (
                  '—'
                )}
              </span>
            </div>
          </div>
        ) : null}
      </header>

      {!selectedShopId ? (
        <section className="dashboard-card dashboard-card--wide">
          <div className="empty-state-panel">
            <p className="empty-state-panel__title">Select a shop to begin</p>
            <p className="empty-state-panel__hint">
              Pick an active shop above to browse the normalized catalog and run the resolver.
            </p>
          </div>
        </section>
      ) : (
        <div className="cc-workspace">
          {/* Catalog browser */}
          <section className="cc-card cc-card--catalog">
            <div className="cc-card__head">
              <div>
                <h2 className="cc-card__title">Catalog products</h2>
                <p className="cc-card__hint">Browse normalized products and manage their aliases.</p>
              </div>
              {catalogQuery.data ? <span className="cc-count-badge">{catalogQuery.data.total}</span> : null}
            </div>

            <div className="cc-search">
              <svg className="cc-search__icon" viewBox="0 0 20 20" aria-hidden="true">
                <path
                  fill="currentColor"
                  d="M8.5 3a5.5 5.5 0 1 0 3.4 9.83l3.13 3.14a1 1 0 0 0 1.42-1.42l-3.14-3.13A5.5 5.5 0 0 0 8.5 3Zm0 2a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7Z"
                />
              </svg>
              <input
                id="catalog-search"
                className="cc-search__input"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Search by title, brand, or alias…"
                aria-label="Search normalized catalog"
              />
              {searchInput ? (
                <button type="button" className="cc-search__clear" onClick={() => setSearchInput('')} aria-label="Clear search">
                  ×
                </button>
              ) : null}
            </div>

            {catalogQuery.isLoading ? <p className="loading-state cc-state">Loading catalog…</p> : null}
            {catalogQuery.isError ? (
              <div className="cc-alert cc-alert--error" role="alert">
                <strong>Could not load catalog.</strong>
                <span>{formatApiError(catalogQuery.error)}</span>
              </div>
            ) : null}
            {!catalogQuery.isLoading && !catalogQuery.isError && items.length === 0 ? (
              <div className="empty-state-panel cc-state">
                <p className="empty-state-panel__title">No normalized products yet</p>
                <p className="empty-state-panel__hint">
                  Run <strong>Reindex catalog</strong> to normalize existing products and build Qdrant vectors.
                </p>
              </div>
            ) : null}

            {items.length > 0 ? (
              <ul className="cc-product-list">
                {items.map((item) => {
                  const isSelected = selectedProduct?.id === item.id;
                  return (
                    <li key={item.id}>
                      <button
                        type="button"
                        className={`cc-product${isSelected ? ' cc-product--selected' : ''}`}
                        onClick={() => setSelectedProduct(isSelected ? null : item)}
                        aria-pressed={isSelected}
                      >
                        <span className="cc-product__main">
                          <span className="cc-product__title">{item.normalized_title}</span>
                          <span className="cc-product__meta">
                            {[item.brand, item.gender, item.color].filter(Boolean).join(' · ') || 'No attributes'}
                          </span>
                        </span>
                        <span
                          className={`cc-dot cc-dot--${item.last_indexed_at ? 'on' : 'off'}`}
                          title={item.last_indexed_at ? 'Indexed' : 'Pending index'}
                        >
                          {item.last_indexed_at ? 'Indexed' : 'Pending'}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : null}

            {catalogQuery.data && catalogQuery.data.total > catalogQuery.data.page_size ? (
              <div className="cc-pagination">
                <button
                  className="button button--ghost-dark"
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                >
                  ← Prev
                </button>
                <span className="cc-pagination__label">
                  Page {page} / {totalPages}
                </span>
                <button
                  className="button button--ghost-dark"
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((current) => current + 1)}
                >
                  Next →
                </button>
              </div>
            ) : null}

            {selectedProduct ? (
              <AliasEditor
                shopId={selectedShopId}
                product={selectedProduct}
                onUpdated={async () => {
                  await queryClient.invalidateQueries({ queryKey: queryKeys.catalogProducts(selectedShopId) });
                  const refreshed = await apiClient.listCatalogProducts(selectedShopId, {
                    search: debouncedSearch || undefined,
                    page,
                    page_size: PAGE_SIZE,
                  });
                  const updated = refreshed.items.find((item) => item.id === selectedProduct.id);
                  if (updated) {
                    setSelectedProduct(updated);
                  }
                }}
              />
            ) : items.length > 0 ? (
              <p className="cc-card__footnote">Select a product to view and edit its aliases.</p>
            ) : null}
          </section>

          {/* Resolver playground */}
          <section className="cc-card cc-card--resolver">
            <div className="cc-card__head">
              <div>
                <h2 className="cc-card__title">Resolver playground</h2>
                <p className="cc-card__hint">Paste a customer DM to resolve the product and variant.</p>
              </div>
              {variantResult ? (
                <span className={`status-pill status-pill--${variantResult.confidence_band}`}>
                  {variantResult.confidence_band} · {Math.round(variantResult.confidence_score * 100)}%
                </span>
              ) : null}
            </div>

            <form className="cc-resolver-form" onSubmit={handleResolveSubmit}>
              <label className="cc-field-label" htmlFor="resolver-message">
                Customer message
              </label>
              <textarea
                id="resolver-message"
                className="cc-textarea"
                rows={3}
                value={messageText}
                onChange={(event) => setMessageText(event.target.value)}
                placeholder="Paste DM text, e.g. مشکی سایز M"
                dir="auto"
              />

              <div className="cc-examples">
                <span className="cc-examples__label">Try:</span>
                {EXAMPLE_MESSAGES.map((example) => (
                  <button
                    key={example.label}
                    type="button"
                    className="cc-chip"
                    onClick={() => setMessageText(example.text)}
                  >
                    {example.label}
                  </button>
                ))}
              </div>

              {selectedProduct ? (
                <p className="cc-resolver-form__scope">
                  Variant search scoped to <strong>{selectedProduct.normalized_title}</strong>.
                </p>
              ) : null}

              <button
                className="button button--primary cc-resolver-form__submit"
                type="submit"
                disabled={!selectedShopId || isResolving || !messageText.trim()}
              >
                {isResolving ? 'Resolving…' : 'Resolve product + variant'}
              </button>
            </form>

            {!hasResults && !isResolving ? (
              <div className="cc-resolver-empty">
                <div className="cc-resolver-empty__badge">AI</div>
                <p>Run the resolver to see ranked product candidates, the matched variant, and a full rationale.</p>
              </div>
            ) : null}

            {productResult ? (
              <div className="cc-candidates">
                <h3 className="cc-subhead">Product candidates</h3>
                {productResult.candidates.length === 0 ? (
                  <p className="empty-state cc-state">No product matches for this message.</p>
                ) : (
                  <ul className="cc-candidate-list">
                    {productResult.candidates.map((candidate, index) => {
                      const isSelected = selectedCandidateId === candidate.product_id;
                      return (
                        <li key={candidate.product_id}>
                          <button
                            type="button"
                            className={`cc-candidate${isSelected ? ' cc-candidate--selected' : ''}`}
                            onClick={() => handleSelectCandidate(candidate)}
                            aria-pressed={isSelected}
                          >
                            <div className="cc-candidate__top">
                              <span className="cc-candidate__rank">#{index + 1}</span>
                              <span className="cc-candidate__title">{candidate.title}</span>
                              <span className={`status-pill status-pill--${candidate.confidence_band}`}>
                                {Math.round(candidate.score * 100)}%
                              </span>
                            </div>
                            <ScoreBar value={candidate.score} band={candidate.confidence_band} />
                            <p className="cc-candidate__rationale">{candidate.rationale}</p>
                            {candidate.matched_aliases.length > 0 ? (
                              <p className="cc-candidate__aliases">
                                {candidate.matched_aliases.map((alias) => (
                                  <span key={alias} className="cc-tag">
                                    {alias}
                                  </span>
                                ))}
                              </p>
                            ) : null}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            ) : null}

            {variantResult ? (
              <div className="cc-variant-results">
                <VariantConfidenceInspector result={variantResult} />
                <WhyThisVariantPanel result={variantResult} trace={activeTrace} />
              </div>
            ) : null}
          </section>

          {/* Trace + operator correction */}
          <section className="cc-card cc-card--trace">
            {activeTrace ? (
              <div className="cc-trace-grid">
                <ResolverTraceViewer trace={activeTrace} />
                <OperatorCorrectionPanel
                  shopId={selectedShopId}
                  trace={activeTrace}
                  productResult={productResult}
                  variantResult={variantResult}
                />
              </div>
            ) : (
              <div className="empty-state-panel">
                <p className="empty-state-panel__title">Resolver trace viewer</p>
                <p className="empty-state-panel__hint">
                  Run a resolver query to inspect candidates, rules fired, missing slots, and submit operator
                  corrections.
                </p>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
