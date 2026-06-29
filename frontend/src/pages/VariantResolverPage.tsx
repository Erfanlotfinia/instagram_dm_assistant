import { FormEvent, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input, Select } from '../components/ui';
import { DataTable, EmptyState, LoadingState } from '../components/data';
import type { Column } from '../components/data';
import { CatalogCompletenessPanel } from '../components/catalog/CatalogCompletenessPanel';
import { cn } from '../lib/cn';
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
    <div>
      <div className="flex items-center justify-between text-xs text-muted">
        <span>{label}</span>
        <strong className="text-fg">{percent}%</strong>
      </div>
      <div
        className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-sunken"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label} confidence`}
      >
        <div
          className={cn(
            'h-full rounded-full transition-all',
            tone === 'success' && 'bg-success',
            tone === 'warning' && 'bg-warning',
            tone === 'default' && 'bg-accent',
          )}
          style={{ width: `${percent}%` }}
        />
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
  const columns: Column<VariantAlternative>[] = [
    {
      key: 'sku',
      header: 'SKU',
      render: (row) => <span className="font-mono text-xs">{row.sku}</span>,
    },
    {
      key: 'color',
      header: 'Color',
      render: (row) => row.normalized_color ?? row.color ?? '—',
    },
    {
      key: 'size',
      header: 'Size',
      render: (row) => row.normalized_size ?? row.size ?? '—',
    },
    {
      key: 'stock',
      header: 'Stock',
      render: (row) => {
        const stock = stockStatus(row.available_stock);
        return (
          <Badge tone={stock.tone}>
            {row.available_stock} · {stock.label}
          </Badge>
        );
      },
    },
    {
      key: 'reason',
      header: 'Why suggested',
      render: (row) => row.reason.replaceAll('_', ' '),
    },
  ];

  return (
    <Card>
      <CardHeader title={title} />
      {rows.length === 0 ? (
        <CardBody>
          <EmptyState title={emptyMessage} />
        </CardBody>
      ) : (
        <DataTable columns={columns} rows={rows} rowKey={(row) => row.variant_id} />
      )}
    </Card>
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
    <Card>
      <CardHeader
        title="Resolver result"
        actions={
          <Badge tone={normalized.matched ? 'success' : 'danger'}>
            {normalized.matched ? 'Matched' : 'No match'}
          </Badge>
        }
      />
      <CardBody className="flex flex-col gap-4">
        {normalized.matched ? (
          <div className="flex flex-wrap items-start justify-between gap-4 rounded-lg border border-success/30 bg-success-soft/20 p-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted">Resolved variant</p>
              <p className="mt-1 font-mono text-lg font-semibold text-fg">{normalized.sku ?? 'Unknown SKU'}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {normalized.normalized_color ? <Badge tone="neutral">{normalized.normalized_color}</Badge> : null}
                {normalized.normalized_size ? <Badge tone="neutral">{normalized.normalized_size}</Badge> : null}
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs font-medium text-muted">Available stock</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-fg">{normalized.available_stock ?? '—'}</p>
              <Badge tone={stock.tone} className="mt-1">
                {stock.label}
              </Badge>
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-danger/30 bg-danger-soft/20 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted">Resolution failed</p>
            <p className="mt-1 text-lg font-semibold text-fg">No exact variant matched the request.</p>
            <p className="mt-1 text-sm text-muted">
              Review normalization and mismatch reasons below, then try aliases or alternatives.
            </p>
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-2">
          <Card as="div" className="shadow-none">
            <CardHeader title="Normalization" />
            <CardBody>
              <dl className="grid gap-3 text-sm">
                <div>
                  <dt className="text-xs font-medium text-muted">Color input</dt>
                  <dd dir="auto" className="mt-0.5 text-fg">
                    {rawColor || '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-muted">Normalized color</dt>
                  <dd className="mt-0.5 text-fg">{normalized.normalized_color ?? '—'}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-muted">Size input</dt>
                  <dd className="mt-0.5 text-fg">{rawSize || '—'}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-muted">Normalized size</dt>
                  <dd className="mt-0.5 text-fg">{normalized.normalized_size ?? '—'}</dd>
                </div>
              </dl>
            </CardBody>
          </Card>

          <Card as="div" className="shadow-none">
            <CardHeader title="Confidence" />
            <CardBody className="flex flex-col gap-3">
              <ConfidenceMeter
                label="Overall"
                value={normalized.confidence}
                tone={normalized.matched ? 'success' : 'warning'}
              />
              <ConfidenceMeter label="Color" value={normalized.color_confidence ?? 0} />
              <ConfidenceMeter label="Size" value={normalized.size_confidence ?? 0} />
            </CardBody>
          </Card>
        </div>

        {mismatchReasons.length > 0 ? (
          <Card as="div" className="shadow-none">
            <CardHeader title="Mismatch reasons" />
            <CardBody>
              <div className="flex flex-wrap gap-2">
                {mismatchReasons.map((reason) => (
                  <Badge key={reason} tone="warning">
                    {formatMismatchReason(reason)}
                  </Badge>
                ))}
              </div>
            </CardBody>
          </Card>
        ) : null}

        {showAlternatives ? (
          <AlternativeTable
            title="Suggested alternatives"
            rows={alternatives}
            emptyMessage="No alternative variants returned."
          />
        ) : null}

        <details className="rounded-lg border border-border">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-accent hover:underline">
            Technical details
          </summary>
          <div className="border-t border-border px-4 py-3">
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              {normalized.variant_id ? (
                <div>
                  <dt className="text-xs font-medium text-muted">Variant ID</dt>
                  <dd className="mt-0.5">
                    <code className="text-xs">{normalized.variant_id}</code>
                  </dd>
                </div>
              ) : null}
              <div>
                <dt className="text-xs font-medium text-muted">Overall confidence</dt>
                <dd className="mt-0.5 text-fg">{formatConfidence(normalized.confidence)}</dd>
              </div>
            </dl>
            <pre className="mt-3 max-h-64 overflow-auto rounded-md bg-surface-sunken p-3 text-xs text-subtle">
              {JSON.stringify(normalized, null, 2)}
            </pre>
          </div>
        </details>
      </CardBody>
    </Card>
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
    <HubPage
      eyebrow="Catalog intelligence"
      title="Product option resolver test"
      description="Test backend-only normalization, variant matching, stock checks, and alternatives without calling the LLM."
    >
      <CatalogCompletenessPanel shopId={selectedShopId} />
      <Card>
        <CardHeader
          title="Test input"
          description={`Pick a product, enter raw customer color/size text, then run the resolver against ${selectedShop?.name ?? 'the selected shop'}.`}
        />
        <CardBody className="flex flex-col gap-4">
          {!selectedShopId ? (
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          ) : (
            <form className="flex flex-col gap-4" onSubmit={submit}>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Field label="Product" className="sm:col-span-2 lg:col-span-4">
                  <Select
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
                  </Select>
                </Field>

                <Field label="Raw color">
                  <Input
                    value={rawColor}
                    onChange={(event) => setRawColor(event.target.value)}
                    placeholder="مشکی"
                    dir="auto"
                  />
                </Field>

                <Field label="Raw size">
                  <Input value={rawSize} onChange={(event) => setRawSize(event.target.value)} placeholder="L" />
                </Field>

                <Field label="Quantity">
                  <Input
                    type="number"
                    min={1}
                    value={quantity}
                    onChange={(event) => setQuantity(Number(event.target.value) || 1)}
                  />
                </Field>
              </div>

              <Field label="Example inputs">
                <div className="flex flex-wrap gap-2" role="group" aria-label="Example resolver inputs">
                  {EXAMPLE_INPUTS.map((example) => (
                    <Button key={example.label} type="button" variant="secondary" size="sm" onClick={() => applyExample(example)}>
                      {example.label}
                    </Button>
                  ))}
                </div>
              </Field>

              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={!canSubmit}>
                  {resolver.isPending ? 'Running resolver…' : 'Run resolver'}
                </Button>
                <Button type="button" variant="ghost" onClick={resetForm}>
                  Reset
                </Button>
              </div>
            </form>
          )}

          {productsQuery.isError ? (
            <div className="rounded-lg border border-danger/30 bg-danger-soft/20 p-4">
              <p className="text-sm text-danger">
                {productsQuery.error instanceof Error
                  ? productsQuery.error.message
                  : 'Failed to load products'}
              </p>
              <Button type="button" variant="ghost" size="sm" className="mt-2" onClick={() => void productsQuery.refetch()}>
                Retry loading products
              </Button>
            </div>
          ) : null}

          {resolver.isError ? (
            <div className="rounded-lg border border-danger/30 bg-danger-soft/20 p-4">
              <p className="text-sm text-danger">
                {resolver.error instanceof Error ? resolver.error.message : 'Resolver request failed'}
              </p>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="mt-2"
                onClick={() => resolver.mutate()}
                disabled={!canSubmit}
              >
                Retry resolver
              </Button>
            </div>
          ) : null}
        </CardBody>
      </Card>

      {resolver.isPending ? (
        <Card>
          <CardBody>
            <LoadingState label="Running product option resolver…" />
          </CardBody>
        </Card>
      ) : null}

      {resolver.data ? <ResolverResultPanel result={resolver.data} rawColor={rawColor} rawSize={rawSize} /> : null}
    </HubPage>
  );
}
