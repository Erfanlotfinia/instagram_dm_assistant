import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { AliasEditor } from '../components/catalog/AliasEditor';
import { OperatorCorrectionPanel } from '../components/catalog/OperatorCorrectionPanel';
import { ResolverTraceViewer } from '../components/catalog/ResolverTraceViewer';
import { VariantConfidenceInspector } from '../components/catalog/VariantConfidenceInspector';
import { WhyThisVariantPanel } from '../components/catalog/WhyThisVariantPanel';
import { EmptyState, KpiCard, LoadingState } from '../components/data';
import { HubPage } from '../components/shell/HubPage';
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  Field,
  FilterChip,
  Input,
  ScoreBar,
  SectionPanel,
} from '../components/ui';
import { cn } from '../lib/cn';
import { confidenceBandTone } from '../lib/confidenceBand';
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

function WorkflowStep({
  index,
  label,
  active,
  done,
}: {
  index: number;
  label: string;
  active?: boolean;
  done?: boolean;
}) {
  return (
    <li
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        done && 'bg-success-soft text-success',
        active && !done && 'bg-accent-soft text-accent',
        !active && !done && 'bg-surface-sunken text-subtle',
      )}
    >
      <span className="font-mono text-[10px] opacity-80">{index}</span>
      {label}
    </li>
  );
}

function ProductCandidateCard({
  candidate,
  rank,
  selected,
  onSelect,
}: {
  candidate: ProductCandidate;
  rank: number;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        className={cn(
          'w-full rounded-xl border p-3 text-left transition-all',
          selected
            ? 'border-accent bg-accent-soft shadow-[inset_0_0_0_1px_var(--color-accent)]'
            : 'border-border bg-surface hover:border-accent/35 hover:bg-surface-sunken/50',
        )}
        onClick={onSelect}
        aria-pressed={selected}
      >
        <div className="flex items-start gap-3">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface-sunken font-mono text-xs font-semibold text-muted">
            {rank}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <p className="font-medium leading-snug text-fg">{candidate.title}</p>
              <Badge tone={confidenceBandTone(candidate.confidence_band)}>
                {Math.round(candidate.score * 100)}%
              </Badge>
            </div>
            <ScoreBar value={candidate.score} band={candidate.confidence_band} className="mt-2.5" />
            <p className="mt-2 text-sm leading-relaxed text-muted">{candidate.rationale}</p>
            {candidate.matched_aliases.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-1">
                {candidate.matched_aliases.map((alias) => (
                  <Badge key={alias} tone="neutral">
                    {alias}
                  </Badge>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </button>
    </li>
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
  const hasMessage = messageText.trim().length > 0;

  return (
    <HubPage
      className="mx-auto flex w-full max-w-7xl flex-col gap-5"
      eyebrow="Catalog intelligence"
      title="Catalog Copilot"
      description="Normalize catalog entries, run hybrid retrieval, and resolve messy customer DMs to the right product and variant — with full trace visibility and operator review."
      actions={
        <>
          <Button
            type="button"
            disabled={!selectedShopId || reindexMutation.isPending}
            onClick={() => reindexMutation.mutate()}
          >
            {reindexMutation.isPending ? 'Reindexing…' : 'Reindex catalog'}
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={!selectedShopId || catalogQuery.isFetching}
            onClick={() => void catalogQuery.refetch()}
          >
            {catalogQuery.isFetching ? 'Refreshing…' : 'Refresh'}
          </Button>
        </>
      }
    >
      {!selectedShopId ? (
        <Card>
          <CardBody>
            <EmptyState
              title="Select a shop to begin"
              description="Use the shop switcher in the top bar to browse the normalized catalog and run the resolver."
            />
          </CardBody>
        </Card>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard label="Normalized products" value={catalogQuery.data?.total ?? '—'} />
            <KpiCard
              label="Indexed on page"
              value={catalogQuery.isLoading ? '…' : `${indexedCount}/${items.length}`}
            />
            <KpiCard label="Product candidates" value={productResult?.candidates.length ?? '—'} />
            <KpiCard
              label="Last confidence"
              value={
                activeTrace ? (
                  <Badge tone={confidenceBandTone(activeTrace.confidence_band)}>
                    {activeTrace.confidence_band}
                  </Badge>
                ) : (
                  '—'
                )
              }
            />
          </div>

          <div className="grid items-start gap-5 lg:grid-cols-[minmax(300px,360px)_minmax(0,1fr)]">
            {/* ── Catalog browser ── */}
            <Card className="flex flex-col lg:sticky lg:top-20 lg:max-h-[calc(100vh-7rem)]">
              <CardHeader
                title="Catalog browser"
                description="Search products and manage aliases."
                actions={catalogQuery.data ? <Badge tone="neutral">{catalogQuery.data.total}</Badge> : undefined}
              />
              <CardBody className="flex min-h-0 flex-1 flex-col gap-4">
                <div className="relative shrink-0">
                  <Input
                    id="catalog-search"
                    value={searchInput}
                    onChange={(event) => setSearchInput(event.target.value)}
                    placeholder="Search title, brand, alias…"
                    aria-label="Search normalized catalog"
                    className="pl-9 pr-8"
                  />
                  <svg
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle"
                    viewBox="0 0 20 20"
                    aria-hidden="true"
                  >
                    <path
                      fill="currentColor"
                      d="M8.5 3a5.5 5.5 0 1 0 3.4 9.83l3.13 3.14a1 1 0 0 0 1.42-1.42l-3.14-3.13A5.5 5.5 0 0 0 8.5 3Zm0 2a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7Z"
                    />
                  </svg>
                  {searchInput ? (
                    <button
                      type="button"
                      className="absolute right-2 top-1/2 -translate-y-1/2 rounded px-1.5 text-muted hover:bg-surface-sunken hover:text-fg"
                      onClick={() => setSearchInput('')}
                      aria-label="Clear search"
                    >
                      ×
                    </button>
                  ) : null}
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto">
                  {catalogQuery.isLoading ? <LoadingState label="Loading catalog…" /> : null}
                  {catalogQuery.isError ? (
                    <div
                      className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger"
                      role="alert"
                    >
                      <strong>Could not load catalog.</strong> {formatApiError(catalogQuery.error)}
                    </div>
                  ) : null}
                  {!catalogQuery.isLoading && !catalogQuery.isError && items.length === 0 ? (
                    <EmptyState
                      title="No normalized products"
                      description="Run Reindex catalog to build vectors and searchable aliases."
                    />
                  ) : null}

                  {items.length > 0 ? (
                    <ul className="flex flex-col gap-1.5 pr-1">
                      {items.map((item) => {
                        const isSelected = selectedProduct?.id === item.id;
                        return (
                          <li key={item.id}>
                            <button
                              type="button"
                              className={cn(
                                'flex w-full items-center gap-2.5 rounded-lg border px-3 py-2.5 text-left transition-colors',
                                isSelected
                                  ? 'border-accent bg-accent-soft'
                                  : 'border-transparent bg-surface-sunken/60 hover:border-border hover:bg-surface-sunken',
                              )}
                              onClick={() => setSelectedProduct(isSelected ? null : item)}
                              aria-pressed={isSelected}
                            >
                              <span
                                className={cn(
                                  'h-2 w-2 shrink-0 rounded-full',
                                  item.last_indexed_at ? 'bg-success' : 'bg-warning',
                                )}
                                title={item.last_indexed_at ? 'Indexed' : 'Pending index'}
                                aria-hidden="true"
                              />
                              <span className="min-w-0 flex-1">
                                <span className="block truncate text-sm font-medium text-fg">
                                  {item.normalized_title}
                                </span>
                                <span className="block truncate text-xs text-muted">
                                  {[item.brand, item.gender, item.color].filter(Boolean).join(' · ') ||
                                    'No attributes'}
                                </span>
                              </span>
                            </button>
                          </li>
                        );
                      })}
                    </ul>
                  ) : null}
                </div>

                {catalogQuery.data && catalogQuery.data.total > catalogQuery.data.page_size ? (
                  <div className="flex shrink-0 items-center justify-between gap-2 border-t border-border pt-3">
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((current) => Math.max(1, current - 1))}
                    >
                      Prev
                    </Button>
                    <span className="text-xs text-muted">
                      {page} / {totalPages}
                    </span>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage((current) => current + 1)}
                    >
                      Next
                    </Button>
                  </div>
                ) : null}

                {selectedProduct ? (
                  <div className="shrink-0 border-t border-border pt-4">
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
                  </div>
                ) : items.length > 0 ? (
                  <p className="shrink-0 border-t border-border pt-3 text-xs text-muted">
                    Select a product to scope variant resolution or edit aliases.
                  </p>
                ) : null}
              </CardBody>
            </Card>

            {/* ── Resolver workspace ── */}
            <div className="flex flex-col gap-5">
              <Card>
                <CardHeader
                  title="Resolver playground"
                  description="Paste a customer DM. The pipeline ranks products, resolves variants, and records a full audit trace."
                  actions={
                    variantResult ? (
                      <Badge tone={confidenceBandTone(variantResult.confidence_band)}>
                        {variantResult.confidence_band} · {Math.round(variantResult.confidence_score * 100)}%
                      </Badge>
                    ) : undefined
                  }
                />
                <CardBody className="flex flex-col gap-5">
                  <ol className="flex flex-wrap gap-2" aria-label="Resolver workflow">
                    <WorkflowStep index={1} label="Message" active={hasMessage} done={hasMessage} />
                    <WorkflowStep index={2} label="Product match" done={Boolean(productResult)} active={isResolving} />
                    <WorkflowStep index={3} label="Variant" done={Boolean(variantResult)} />
                    <WorkflowStep index={4} label="Trace" done={Boolean(activeTrace)} />
                  </ol>

                  {selectedProduct ? (
                    <div className="flex items-center gap-2 rounded-lg border border-accent/25 bg-accent-soft/40 px-3 py-2 text-sm">
                      <Badge tone="accent">Scoped</Badge>
                      <span className="text-muted">
                        Variant resolution limited to{' '}
                        <strong className="text-fg">{selectedProduct.normalized_title}</strong>
                      </span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="ml-auto"
                        onClick={() => setSelectedProduct(null)}
                      >
                        Clear scope
                      </Button>
                    </div>
                  ) : null}

                  <SectionPanel title="Customer message" variant="compose">
                    <form className="flex flex-col gap-3" onSubmit={handleResolveSubmit}>
                      <Field label={<span className="visually-hidden">Customer message</span>} htmlFor="resolver-message">
                        <textarea
                          id="resolver-message"
                          rows={4}
                          value={messageText}
                          onChange={(event) => setMessageText(event.target.value)}
                          placeholder="Paste DM text — Persian or English, e.g. مشکی سایز M"
                          dir="auto"
                          className="w-full resize-y rounded-lg border border-border bg-surface px-3 py-2.5 text-sm leading-relaxed text-fg placeholder:text-subtle focus:border-accent focus:outline-none"
                        />
                      </Field>

                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-medium text-muted">Examples</span>
                        {EXAMPLE_MESSAGES.map((example) => (
                          <FilterChip
                            key={example.label}
                            active={messageText === example.text}
                            onClick={() => setMessageText(example.text)}
                          >
                            {example.label}
                          </FilterChip>
                        ))}
                      </div>

                      <Button type="submit" disabled={!selectedShopId || isResolving || !messageText.trim()}>
                        {isResolving ? 'Resolving product + variant…' : 'Run resolver'}
                      </Button>
                    </form>
                  </SectionPanel>

                  {isResolving ? <LoadingState label="Running hybrid retrieval and variant match…" /> : null}

                  {!hasResults && !isResolving ? (
                    <EmptyState
                      title="No resolver results yet"
                      description="Enter a customer message and run the resolver to see ranked products, variant confidence, and operator feedback options."
                    />
                  ) : null}

                  {productResult && !isResolving ? (
                    <section className="flex flex-col gap-3" aria-label="Product candidates">
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="text-sm font-semibold text-fg">Product candidates</h3>
                        <span className="text-xs text-muted">{productResult.candidates.length} matches</span>
                      </div>
                      {productResult.candidates.length === 0 ? (
                        <EmptyState title="No product matches for this message" />
                      ) : (
                        <ul className="flex flex-col gap-2">
                          {productResult.candidates.map((candidate, index) => (
                            <ProductCandidateCard
                              key={candidate.product_id}
                              candidate={candidate}
                              rank={index + 1}
                              selected={selectedCandidateId === candidate.product_id}
                              onSelect={() => handleSelectCandidate(candidate)}
                            />
                          ))}
                        </ul>
                      )}
                    </section>
                  ) : null}

                  {variantResult && !isResolving ? (
                    <section className="grid gap-4" aria-label="Variant resolution">
                      <VariantConfidenceInspector result={variantResult} />
                      <WhyThisVariantPanel result={variantResult} trace={activeTrace} />
                    </section>
                  ) : null}
                </CardBody>
              </Card>
            </div>
          </div>

          {/* ── Full-width trace & correction ── */}
          <Card>
            <CardHeader
              title="Audit trace & operator correction"
              description="Inspect rules fired, candidate scores, and submit feedback to improve future resolution."
              actions={
                activeTrace ? (
                  <Badge tone={confidenceBandTone(activeTrace.confidence_band)}>
                    {activeTrace.confidence_band}
                  </Badge>
                ) : undefined
              }
            />
            <CardBody>
              {activeTrace ? (
                <div className="grid gap-6 lg:grid-cols-2">
                  <ResolverTraceViewer trace={activeTrace} />
                  <div className="rounded-lg border border-border bg-surface-sunken p-4">
                    <OperatorCorrectionPanel
                      shopId={selectedShopId}
                      trace={activeTrace}
                      productResult={productResult}
                      variantResult={variantResult}
                    />
                  </div>
                </div>
              ) : (
                <EmptyState
                  title="Trace will appear after a resolver run"
                  description="Run the resolver above to inspect retrieval evidence, rules fired, missing slots, and submit operator corrections."
                />
              )}
            </CardBody>
          </Card>
        </>
      )}
    </HubPage>
  );
}
