import { useMemo, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';
import { z } from 'zod';

import { filterBySearch, Pagination, paginateItems } from '../components/Pagination';
import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';

const PAGE_SIZE = 15;

const productSchema = z.object({
  title: z.string().min(1, 'Title is required'),
  description: z.string().optional(),
  base_price: z.string().min(1, 'Price is required'),
  currency: z.string().length(3, 'Use a 3-letter currency code'),
});

type ProductFormValues = z.infer<typeof productSchema>;

export function ProductsPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');

  const productsQuery = useQuery({
    queryKey: queryKeys.products(selectedShopId),
    queryFn: () => apiClient.listProducts(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const metricsQuery = useQuery({
    queryKey: queryKeys.dashboardMetrics(selectedShopId),
    queryFn: () => apiClient.getDashboardMetrics(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const lowStockProductIds = useMemo(() => {
    const variants = metricsQuery.data?.low_stock_variants ?? [];
    return new Set(variants.map((variant) => variant.product_id));
  }, [metricsQuery.data]);

  const filteredProducts = useMemo(() => {
    const products = productsQuery.data ?? [];
    return filterBySearch(products, (product) => `${product.title} ${product.description ?? ''}`, search);
  }, [productsQuery.data, search]);

  const pageItems = useMemo(
    () => paginateItems(filteredProducts, page, PAGE_SIZE),
    [filteredProducts, page],
  );

  const form = useForm<ProductFormValues>({
    resolver: zodResolver(productSchema),
    defaultValues: { title: '', description: '', base_price: '', currency: 'USD' },
  });

  const createMutation = useMutation({
    mutationFn: (values: ProductFormValues) =>
      apiClient.createProduct(selectedShopId, {
        title: values.title,
        description: values.description || undefined,
        base_price: values.base_price,
        currency: values.currency,
      }),
    onSuccess: () => {
      form.reset({ title: '', description: '', base_price: '', currency: 'USD' });
      showToast('Product created.', 'success');
      queryClient.invalidateQueries({ queryKey: queryKeys.products(selectedShopId) });
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Create failed', 'error'),
  });

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Catalog</p>
        <h1>Products</h1>
        <p>Manage your shop product catalog and monitor low-stock items.</p>
        <ShopSelector />

        <label className="form-field">
          <span>Search products</span>
          <input
            type="search"
            value={search}
            onChange={(event) => {
              setPage(1);
              setSearch(event.target.value);
            }}
          />
        </label>

        <form className="inline-form" onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}>
          <label className="form-field">
            <span>Title</span>
            <input {...form.register('title')} />
            {form.formState.errors.title ? (
              <span className="field-error">{form.formState.errors.title.message}</span>
            ) : null}
          </label>
          <label className="form-field">
            <span>Description</span>
            <input {...form.register('description')} />
          </label>
          <label className="form-field">
            <span>Base price</span>
            <input type="number" step="0.01" min="0.01" {...form.register('base_price')} />
          </label>
          <label className="form-field">
            <span>Currency</span>
            <input maxLength={3} {...form.register('currency')} />
          </label>
          <button className="button button--primary" type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? 'Creating...' : 'Create product'}
          </button>
        </form>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        {productsQuery.isLoading ? <p className="loading-state">Loading products...</p> : null}

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Status</th>
                <th>Price</th>
                <th>Stock alert</th>
              </tr>
            </thead>
            <tbody>
              {pageItems.map((product) => (
                <tr key={product.id} className={lowStockProductIds.has(product.id) ? 'row-warning' : undefined}>
                  <td>
                    <Link
                      className="table-link"
                      to={`/products/${product.id}?shopId=${selectedShopId}`}
                    >
                      {product.title}
                    </Link>
                  </td>
                  <td>{product.status}</td>
                  <td>
                    {product.base_price} {product.currency}
                  </td>
                  <td>{lowStockProductIds.has(product.id) ? 'Low stock' : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredProducts.length === 0 && !productsQuery.isLoading ? (
            <p className="empty-state">No products yet.</p>
          ) : null}
        </div>

        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          totalItems={filteredProducts.length}
          onPageChange={setPage}
        />
      </section>
    </div>
  );
}
