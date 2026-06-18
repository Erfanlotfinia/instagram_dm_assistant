import { useMemo, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';
import { z } from 'zod';

import { filterBySearch, Pagination, paginateItems } from '../components/Pagination';
import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input } from '../components/ui';
import { DataTable, FilterBar } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { Product } from '../types/product';

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

  const pageItems = useMemo(() => paginateItems(filteredProducts, page, PAGE_SIZE), [filteredProducts, page]);

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

  const columns: Column<Product>[] = [
    {
      key: 'title',
      header: 'Product',
      render: (product) => (
        <Link
          className="font-medium text-accent hover:underline"
          to={`/catalog/products/${product.id}?shopId=${selectedShopId}`}
        >
          {product.title}
        </Link>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (product) => <Badge tone="neutral">{product.status}</Badge>,
    },
    {
      key: 'price',
      header: 'Price',
      align: 'right',
      render: (product) => (
        <span className="tabular-nums">
          {product.base_price} {product.currency}
        </span>
      ),
    },
    {
      key: 'stock',
      header: 'Stock',
      render: (product) =>
        lowStockProductIds.has(product.id) ? (
          <Badge tone="warning">Low stock</Badge>
        ) : (
          <span className="text-subtle">—</span>
        ),
    },
  ];

  return (
    <HubPage
      eyebrow="Catalog"
      title="Products"
      description="Manage your shop catalog and monitor low-stock variants."
    >
      <Card>
        <CardHeader title="Add product" description="Create a new catalog item for this shop." />
        <CardBody>
          <form
            className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
            onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}
          >
            <Field label="Title">
              <Input {...form.register('title')} />
              {form.formState.errors.title ? (
                <span className="text-xs text-danger">{form.formState.errors.title.message}</span>
              ) : null}
            </Field>
            <Field label="Description">
              <Input {...form.register('description')} />
            </Field>
            <Field label="Base price">
              <Input type="number" step="0.01" min="0.01" {...form.register('base_price')} />
            </Field>
            <Field label="Currency">
              <Input maxLength={3} {...form.register('currency')} />
            </Field>
            <div className="flex items-end sm:col-span-2 lg:col-span-4">
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Creating…' : 'Create product'}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      <Card>
        <div className="border-b border-border px-5 py-3">
          <FilterBar search={search} onSearch={(value) => { setPage(1); setSearch(value); }} searchPlaceholder="Search products…" />
        </div>
        <DataTable
          columns={columns}
          rows={pageItems}
          rowKey={(product) => product.id}
          isLoading={productsQuery.isLoading}
          error={productsQuery.error instanceof Error ? productsQuery.error.message : null}
          emptyTitle="No products yet"
          emptyDescription="Create your first product above."
        />
        <Pagination page={page} pageSize={PAGE_SIZE} totalItems={filteredProducts.length} onPageChange={setPage} />
      </Card>
    </HubPage>
  );
}
