import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { Badge, Button, Card, CardBody, CardHeader } from '../ui';
import { EmptyState, ErrorState, KpiCard, LoadingState } from '../data';
import { apiClient } from '../../services/apiClient';
import { evaluateCatalogCompleteness, probeVariants } from '../../lib/readiness';
import type { AttributeAlias } from '../../types/fashion';
import type { InstagramProductMap } from '../../types/product';
import type { CatalogCompletenessScore } from '../../types/sprint2Readiness';

export interface CatalogCompletenessPanelProps {
  shopId: string | null | undefined;
}

function scoreTone(score: number): 'success' | 'warning' | 'danger' {
  if (score >= 80) return 'success';
  if (score >= 50) return 'warning';
  return 'danger';
}

/**
 * Catalog completeness panel. Renders the completeness score, product counts,
 * missing price/image/variant counts, alias/mapping completeness, and
 * recommended next actions.
 *
 * Variant counts are NOT auto-fetched on load (avoids N+1). The optional
 * "Analyze variants" button runs a bounded `probeVariants` over the first
 * 50 active products (concurrency 4) and re-computes the variants check.
 */
export function CatalogCompletenessPanel({ shopId }: CatalogCompletenessPanelProps) {
  const [variantProbe, setVariantProbe] = useState<{ checked: number; missingVariants: number } | null>(null);
  const [probing, setProbing] = useState(false);
  const [probeError, setProbeError] = useState<string | null>(null);

  const productsQuery = useQuery({
    queryKey: ['products', shopId],
    queryFn: () => apiClient.listProducts(shopId!),
    enabled: Boolean(shopId),
  });
  const aliasesQuery = useQuery({
    queryKey: ['attribute-aliases', shopId],
    queryFn: () => apiClient.listAttributeAliases(shopId!),
    enabled: Boolean(shopId),
  });
  const mappingsQuery = useQuery({
    queryKey: ['instagram-product-maps', shopId],
    queryFn: () => apiClient.listInstagramProductMaps(shopId!),
    enabled: Boolean(shopId),
  });

  const score = useMemo<CatalogCompletenessScore>(() => {
    return evaluateCatalogCompleteness({
      products: productsQuery.data ?? [],
      attributeAliases: (aliasesQuery.data as AttributeAlias[] | undefined) ?? null,
      productMappings: (mappingsQuery.data as InstagramProductMap[] | undefined) ?? null,
      variantProbe,
    });
  }, [productsQuery.data, aliasesQuery.data, mappingsQuery.data, variantProbe]);

  if (!shopId) {
    return (
      <Card>
        <CardHeader title="Catalog completeness" />
        <CardBody>
          <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
        </CardBody>
      </Card>
    );
  }

  if (productsQuery.isLoading || aliasesQuery.isLoading || mappingsQuery.isLoading) {
    return (
      <Card>
        <CardHeader title="Catalog completeness" />
        <CardBody>
          <LoadingState label="Loading catalog…" />
        </CardBody>
      </Card>
    );
  }

  if (productsQuery.isError) {
    return (
      <Card>
        <CardHeader title="Catalog completeness" />
        <CardBody>
          <ErrorState
            message={productsQuery.error instanceof Error ? productsQuery.error.message : 'Failed to load catalog'}
          />
        </CardBody>
      </Card>
    );
  }

  async function handleAnalyzeVariants() {
    if (!shopId || !productsQuery.data) return;
    setProbing(true);
    setProbeError(null);
    try {
      const activeProducts = productsQuery.data.filter((p) => p.status === 'active');
      const result = await probeVariants(shopId, activeProducts, { maxProducts: 50, concurrency: 4 });
      setVariantProbe(result);
    } catch (err) {
      setProbeError(err instanceof Error ? err.message : 'Variant analysis failed.');
    } finally {
      setProbing(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Catalog completeness"
        description="Score blends product, price, image, variant, alias, and mapping completeness."
        actions={<Badge tone={scoreTone(score.score)}>{score.score}%</Badge>}
      />
      <CardBody className="flex flex-col gap-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard label="Total products" value={String(score.productsTotal)} />
          <KpiCard label="Active products" value={String(score.productsActive)} tone={score.productsActive > 0 ? 'success' : 'danger'} />
          <KpiCard
            label="Missing price"
            value={String(score.productsMissingPrice ?? 0)}
            tone={(score.productsMissingPrice ?? 0) === 0 ? 'success' : 'danger'}
          />
          <KpiCard
            label="Missing image"
            value={String(score.productsMissingImage ?? 0)}
            tone={(score.productsMissingImage ?? 0) === 0 ? 'success' : 'warning'}
          />
          <KpiCard label="Attribute aliases" value={String(score.attributesConfigured)} tone={score.attributesConfigured > 0 ? 'success' : 'warning'} />
          <KpiCard label="Product mappings" value={String(score.mappingsConfigured)} tone={score.mappingsConfigured > 0 ? 'success' : 'warning'} />
          <KpiCard
            label="Variants"
            value={score.variantsUnknown ? 'Unknown' : `${score.productsMissingVariants ?? 0} missing`}
            tone={score.variantsUnknown ? 'warning' : (score.productsMissingVariants ?? 0) === 0 ? 'success' : 'warning'}
          />
          <KpiCard label="Variants checked" value={String(score.variantsChecked ?? 0)} />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" size="sm" onClick={handleAnalyzeVariants} disabled={probing || score.productsActive === 0}>
            {probing ? 'Analyzing…' : 'Analyze variants'}
          </Button>
          {score.productsActive > 0 ? (
            <span className="text-xs text-muted">
              Checks up to 50 active products with bounded concurrency.
            </span>
          ) : null}
        </div>

        {probeError ? (
          <p className="text-xs text-danger" role="alert">{probeError}</p>
        ) : null}

        {score.blockingReasons.length > 0 ? (
          <div className="rounded-md border border-danger/30 bg-danger-soft/20 px-3 py-2 text-sm text-fg" role="alert">
            <p className="font-medium">Blocking reasons:</p>
            <ul className="mt-1 list-inside list-disc space-y-0.5 text-muted">
              {score.blockingReasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {score.warnings.length > 0 ? (
          <div className="rounded-md border border-warning/30 bg-warning-soft/20 px-3 py-2 text-sm text-fg" role="note">
            <p className="font-medium">Warnings:</p>
            <ul className="mt-1 list-inside list-disc space-y-0.5 text-muted">
              {score.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <Link className="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-accent hover:bg-surface-sunken" to="/catalog/products">
            Products →
          </Link>
          <Link className="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-accent hover:bg-surface-sunken" to="/catalog/attributes">
            Attributes →
          </Link>
          <Link className="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-accent hover:bg-surface-sunken" to="/catalog/resolver">
            Resolver →
          </Link>
          <Link className="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-accent hover:bg-surface-sunken" to="/catalog/mapping">
            Mapping →
          </Link>
          {(score.productsMissingPrice ?? 0) > 0 || (score.productsMissingVariants ?? 0) > 0 ? (
            <Link className="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-accent hover:bg-surface-sunken" to="/analytics/recovery">
              Revenue recovery →
            </Link>
          ) : null}
        </div>
      </CardBody>
    </Card>
  );
}
