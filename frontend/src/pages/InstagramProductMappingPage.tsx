import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input, Select } from '../components/ui';
import { DataTable, EmptyState } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { InstagramProductMap, ResolveInstagramProductResponse } from '../types/product';

export function InstagramProductMappingPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [selectedProductId, setSelectedProductId] = useState('');
  const [postUrl, setPostUrl] = useState('');
  const [mediaId, setMediaId] = useState('');
  const [testPostUrl, setTestPostUrl] = useState('');
  const [resolveResult, setResolveResult] = useState<ResolveInstagramProductResponse | null>(null);

  const accountsQuery = useQuery({
    queryKey: ['shops', selectedShopId, 'instagram-accounts'],
    queryFn: () => apiClient.listInstagramAccounts(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const productsQuery = useQuery({
    queryKey: queryKeys.products(selectedShopId),
    queryFn: () => apiClient.listProducts(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const mapsQuery = useQuery({
    queryKey: queryKeys.instagramMaps(selectedShopId),
    queryFn: () => apiClient.listInstagramProductMaps(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const createMapMutation = useMutation({
    mutationFn: () =>
      apiClient.createInstagramProductMap(selectedShopId, {
        instagram_account_id: selectedAccountId,
        instagram_post_url: postUrl,
        instagram_media_id: mediaId || undefined,
        product_id: selectedProductId,
        confidence_source: 'manual',
      }),
    onSuccess: () => {
      setPostUrl('');
      setMediaId('');
      showToast('Mapping saved.', 'success');
      queryClient.invalidateQueries({ queryKey: queryKeys.instagramMaps(selectedShopId) });
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Save failed', 'error'),
  });

  const resolveMutation = useMutation({
    mutationFn: () =>
      apiClient.resolveInstagramProduct(selectedShopId, {
        instagram_post_url: testPostUrl,
      }),
    onSuccess: (result) => {
      setResolveResult(result);
      if (result.product) {
        showToast(`Resolved: ${result.product.title}`, 'success');
      } else {
        showToast('No product matched for this post.', 'info');
      }
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Resolve failed', 'error'),
  });

  const confirmSemanticMutation = useMutation({
    mutationFn: () =>
      apiClient.createInstagramProductMap(selectedShopId, {
        instagram_account_id: selectedAccountId || accountsQuery.data?.[0]?.id || '',
        instagram_post_url: testPostUrl,
        product_id: resolveResult!.product!.id,
        confidence_source: 'admin_confirmed',
      }),
    onSuccess: () => {
      showToast('Semantic match confirmed and mapping saved.', 'success');
      queryClient.invalidateQueries({ queryKey: queryKeys.instagramMaps(selectedShopId) });
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Confirm failed', 'error'),
  });

  const accounts = accountsQuery.data ?? [];
  const products = productsQuery.data ?? [];
  const maps = mapsQuery.data ?? [];

  const columns: Column<InstagramProductMap>[] = [
    {
      key: 'url',
      header: 'Post URL',
      render: (row) => (
        <a href={row.instagram_post_url} target="_blank" rel="noreferrer" className="text-accent hover:underline">
          {row.instagram_post_url}
        </a>
      ),
    },
    {
      key: 'media',
      header: 'Media ID',
      className: 'hidden md:table-cell',
      render: (row) => <span className="font-mono text-xs">{row.instagram_media_id ?? '—'}</span>,
    },
    {
      key: 'product',
      header: 'Product ID',
      className: 'hidden lg:table-cell',
      render: (row) => <span className="font-mono text-xs">{row.product_id}</span>,
    },
    {
      key: 'source',
      header: 'Source',
      render: (row) => <Badge tone="neutral">{row.confidence_source}</Badge>,
    },
    {
      key: 'active',
      header: 'Active',
      align: 'right',
      render: (row) => <Badge tone={row.is_active ? 'success' : 'neutral'}>{row.is_active ? 'yes' : 'no'}</Badge>,
    },
  ];

  return (
    <HubPage
      eyebrow="Instagram"
      title="Post-to-product mapping"
      description="Link Instagram posts to catalog products for DM order resolution."
    >
      <Card>
        <CardHeader title="Create mapping" description="Manually associate a post URL with a catalog product." />
        <CardBody>
          <form
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault();
              createMapMutation.mutate();
            }}
          >
            <Field label="Instagram account">
              <Select value={selectedAccountId} onChange={(e) => setSelectedAccountId(e.target.value)} required>
                <option value="">Select account</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>@{account.username}</option>
                ))}
              </Select>
            </Field>
            <Field label="Product">
              <Select value={selectedProductId} onChange={(e) => setSelectedProductId(e.target.value)} required>
                <option value="">Select product</option>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>{product.title}</option>
                ))}
              </Select>
            </Field>
            <Field label="Instagram post URL" className="sm:col-span-2">
              <Input value={postUrl} onChange={(e) => setPostUrl(e.target.value)} required />
            </Field>
            <Field label="Media ID (optional)">
              <Input value={mediaId} onChange={(e) => setMediaId(e.target.value)} />
            </Field>
            <div className="flex items-end">
              <Button type="submit" disabled={createMapMutation.isPending}>
                {createMapMutation.isPending ? 'Saving…' : 'Save mapping'}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Test resolve & confirm match"
          description="Paste a post URL to test resolution, then confirm a semantic match if needed."
        />
        <CardBody>
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              resolveMutation.mutate();
            }}
          >
            <Field label="Instagram post URL" className="min-w-[16rem] flex-1">
              <Input value={testPostUrl} onChange={(e) => setTestPostUrl(e.target.value)} required />
            </Field>
            <Button type="submit" disabled={resolveMutation.isPending}>
              {resolveMutation.isPending ? 'Resolving…' : 'Test resolve'}
            </Button>
          </form>

          {resolveResult ? (
            <div className="mt-4 rounded-lg border border-border bg-surface-sunken p-4">
              {resolveResult.product ? (
                <div className="flex flex-col gap-3">
                  <div>
                    <p className="font-medium text-fg">{resolveResult.product.title}</p>
                    <p className="text-sm text-muted">
                      {resolveResult.product.base_price} {resolveResult.product.currency} · Source:{' '}
                      {resolveResult.confidence_source}
                    </p>
                  </div>
                  {resolveResult.confidence_source !== 'manual' ? (
                    <Button
                      type="button"
                      disabled={confirmSemanticMutation.isPending || !selectedAccountId}
                      onClick={() => confirmSemanticMutation.mutate()}
                    >
                      Confirm semantic match
                    </Button>
                  ) : null}
                </div>
              ) : (
                <EmptyState
                  title="No product matched"
                  description="Create a manual mapping above or try a different post URL."
                />
              )}
            </div>
          ) : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Saved mappings" description={`${maps.length} post-to-product links for this shop.`} />
        <DataTable
          columns={columns}
          rows={maps}
          rowKey={(row) => row.id}
          isLoading={mapsQuery.isLoading}
          error={mapsQuery.error instanceof Error ? mapsQuery.error.message : null}
          emptyTitle="No mappings yet"
          emptyDescription="Create your first mapping above."
        />
      </Card>
    </HubPage>
  );
}

export function ProductResolverPage() {
  return <InstagramProductMappingPage />;
}
