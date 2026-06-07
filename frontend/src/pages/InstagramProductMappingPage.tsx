import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { ResolveInstagramProductResponse } from '../types/product';

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

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Instagram</p>
        <h1>Post-to-product mapping</h1>
        <p>Link Instagram posts to catalog products for DM order resolution.</p>
        <ShopSelector />

        <form
          className="inline-form"
          onSubmit={(event) => {
            event.preventDefault();
            createMapMutation.mutate();
          }}
        >
          <label className="form-field">
            <span>Instagram account</span>
            <select
              value={selectedAccountId}
              onChange={(event) => setSelectedAccountId(event.target.value)}
              required
            >
              <option value="">Select account</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  @{account.username}
                </option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>Instagram post URL</span>
            <input value={postUrl} onChange={(event) => setPostUrl(event.target.value)} required />
          </label>
          <label className="form-field">
            <span>Media ID (optional)</span>
            <input value={mediaId} onChange={(event) => setMediaId(event.target.value)} />
          </label>
          <label className="form-field">
            <span>Product</span>
            <select
              value={selectedProductId}
              onChange={(event) => setSelectedProductId(event.target.value)}
              required
            >
              <option value="">Select product</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.title}
                </option>
              ))}
            </select>
          </label>
          <button className="button button--primary" type="submit" disabled={createMapMutation.isPending}>
            {createMapMutation.isPending ? 'Saving...' : 'Save mapping'}
          </button>
        </form>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Test resolve &amp; confirm match</h2>
        <p>Paste a post URL to test resolution, then confirm a semantic match if needed.</p>
        <form
          className="inline-form"
          onSubmit={(event) => {
            event.preventDefault();
            resolveMutation.mutate();
          }}
        >
          <label className="form-field">
            <span>Instagram post URL</span>
            <input value={testPostUrl} onChange={(event) => setTestPostUrl(event.target.value)} required />
          </label>
          <button className="button button--primary" type="submit" disabled={resolveMutation.isPending}>
            {resolveMutation.isPending ? 'Resolving...' : 'Test resolve'}
          </button>
        </form>

        {resolveResult ? (
          <div className="match-panel">
            {resolveResult.product ? (
              <>
                <p>
                  <strong>{resolveResult.product.title}</strong> · {resolveResult.product.base_price}{' '}
                  {resolveResult.product.currency}
                </p>
                <p>Source: {resolveResult.confidence_source}</p>
                {resolveResult.confidence_source !== 'manual' ? (
                  <button
                    className="button button--primary"
                    type="button"
                    disabled={confirmSemanticMutation.isPending || !selectedAccountId}
                    onClick={() => confirmSemanticMutation.mutate()}
                  >
                    Confirm semantic match
                  </button>
                ) : null}
              </>
            ) : (
              <p className="empty-state">No product matched. Create a manual mapping above.</p>
            )}
          </div>
        ) : null}
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Post URL</th>
                <th>Media ID</th>
                <th>Product ID</th>
                <th>Source</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {maps.map((mapping) => (
                <tr key={mapping.id}>
                  <td>{mapping.instagram_post_url}</td>
                  <td>{mapping.instagram_media_id ?? '—'}</td>
                  <td>{mapping.product_id}</td>
                  <td>{mapping.confidence_source}</td>
                  <td>{mapping.is_active ? 'yes' : 'no'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {maps.length === 0 ? <p className="empty-state">No mappings yet.</p> : null}
        </div>
      </section>
    </div>
  );
}

export function ProductResolverPage() {
  return <InstagramProductMappingPage />;
}
