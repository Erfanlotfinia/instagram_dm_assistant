import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input, Select } from '../components/ui';
import { DataTable, EmptyState, LoadingState } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { cn } from '../lib/cn';
import { apiClient } from '../services/apiClient';
import type { Product, ProductVariant } from '../types/product';

export function ProductDetailPage() {
  const { productId } = useParams<{ productId: string }>();
  const [searchParams] = useSearchParams();
  const { selectedShopId, selectedShop } = useShop();
  const shopId = searchParams.get('shopId') ?? selectedShopId;
  const lowStockThreshold = selectedShop?.agent_settings?.low_stock_threshold ?? 5;

  const [product, setProduct] = useState<Product | null>(null);
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [basePrice, setBasePrice] = useState('');
  const [status, setStatus] = useState<Product['status']>('active');
  const [sku, setSku] = useState('');
  const [color, setColor] = useState('');
  const [size, setSize] = useState('');
  const [variantPrice, setVariantPrice] = useState('');
  const [stockQuantity, setStockQuantity] = useState('0');
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isAddingVariant, setIsAddingVariant] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!shopId || !productId) {
      return;
    }

    setIsLoading(true);

    Promise.all([
      apiClient.getProduct(shopId, productId),
      apiClient.listVariants(shopId, productId),
    ])
      .then(([productData, variantData]) => {
        setProduct(productData);
        setTitle(productData.title);
        setDescription(productData.description ?? '');
        setBasePrice(productData.base_price);
        setStatus(productData.status);
        setVariants(variantData);
      })
      .catch(() => {
        setProduct(null);
        setVariants([]);
      })
      .finally(() => setIsLoading(false));
  }, [shopId, productId]);

  async function handleUpdateProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!shopId || !productId) {
      return;
    }

    setError(null);
    setIsSaving(true);

    try {
      const updated = await apiClient.updateProduct(shopId, productId, {
        title,
        description: description || undefined,
        base_price: basePrice,
        status,
      });
      setProduct(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update product');
    } finally {
      setIsSaving(false);
    }
  }

  async function handleAddVariant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!shopId || !productId) {
      return;
    }

    setError(null);
    setIsAddingVariant(true);

    try {
      await apiClient.createVariant(shopId, productId, {
        sku,
        color: color || undefined,
        size: size || undefined,
        price: variantPrice,
        stock_quantity: Number(stockQuantity),
      });
      setSku('');
      setColor('');
      setSize('');
      setVariantPrice('');
      setStockQuantity('0');
      const updated = await apiClient.listVariants(shopId, productId);
      setVariants(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add variant');
    } finally {
      setIsAddingVariant(false);
    }
  }

  const variantColumns: Column<ProductVariant>[] = useMemo(
    () => [
      { key: 'sku', header: 'SKU', render: (variant) => variant.sku },
      { key: 'color', header: 'Color', render: (variant) => variant.color ?? '—' },
      { key: 'size', header: 'Size', render: (variant) => variant.size ?? '—' },
      {
        key: 'price',
        header: 'Price',
        align: 'right',
        render: (variant) => <span className="tabular-nums">{variant.price}</span>,
      },
      {
        key: 'stock',
        header: 'Stock',
        align: 'right',
        render: (variant) => variant.stock_quantity,
      },
      {
        key: 'reserved',
        header: 'Reserved',
        align: 'right',
        render: (variant) => variant.reserved_quantity,
      },
      {
        key: 'available',
        header: 'Available',
        align: 'right',
        render: (variant) => (
          <span className={cn(variant.available_stock <= lowStockThreshold && 'text-warning')}>
            {variant.available_stock}
            {variant.available_stock <= lowStockThreshold ? (
              <Badge tone="warning" className="ml-2">
                Low
              </Badge>
            ) : null}
          </span>
        ),
      },
      {
        key: 'active',
        header: 'Active',
        render: (variant) => (
          <Badge tone={variant.is_active ? 'success' : 'neutral'}>{variant.is_active ? 'yes' : 'no'}</Badge>
        ),
      },
    ],
    [lowStockThreshold],
  );

  if (!shopId) {
    return (
      <HubPage eyebrow="Catalog" title="Product detail" description="View and edit a catalog product.">
        <Card>
          <CardBody>
            <EmptyState
              title="Select a shop"
              description="Open this product from the products list or use the shop switcher in the top bar."
              action={
                <Link to="/catalog/products">
                  <Button variant="secondary" size="sm">
                    Back to products
                  </Button>
                </Link>
              }
            />
          </CardBody>
        </Card>
      </HubPage>
    );
  }

  if (isLoading || !product) {
    return (
      <HubPage eyebrow="Catalog" title="Product detail" description="View and edit a catalog product.">
        <Card>
          <CardBody>
            {isLoading ? (
              <LoadingState label="Loading product…" />
            ) : (
              <EmptyState title="Product not found" description="This product may have been removed." />
            )}
          </CardBody>
        </Card>
      </HubPage>
    );
  }

  return (
    <HubPage
      eyebrow="Catalog"
      title={product.title}
      description="Edit product details and manage variant inventory."
      actions={
        <Link to="/catalog/products">
          <Button variant="secondary" size="sm">
            Back to products
          </Button>
        </Link>
      }
    >
      <Card>
        <CardHeader title="Product details" description="Update title, pricing, and catalog status." />
        <CardBody>
          <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleUpdateProduct}>
            <Field label="Title">
              <Input value={title} onChange={(event) => setTitle(event.target.value)} required />
            </Field>
            <Field label="Description">
              <Input value={description} onChange={(event) => setDescription(event.target.value)} />
            </Field>
            <Field label="Base price">
              <Input
                type="number"
                step="0.01"
                min="0.01"
                value={basePrice}
                onChange={(event) => setBasePrice(event.target.value)}
                required
              />
            </Field>
            <Field label="Status">
              <Select value={status} onChange={(event) => setStatus(event.target.value as Product['status'])}>
                <option value="active">active</option>
                <option value="inactive">inactive</option>
                <option value="archived">archived</option>
              </Select>
            </Field>
            <div className="flex items-end sm:col-span-2">
              <Button type="submit" disabled={isSaving}>
                {isSaving ? 'Saving…' : 'Save product'}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Variants & inventory" description="Add SKUs and track stock levels per variant." />
        <CardBody className="flex flex-col gap-4">
          <form className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" onSubmit={handleAddVariant}>
            <Field label="SKU">
              <Input value={sku} onChange={(event) => setSku(event.target.value)} required />
            </Field>
            <Field label="Color">
              <Input value={color} onChange={(event) => setColor(event.target.value)} />
            </Field>
            <Field label="Size">
              <Input value={size} onChange={(event) => setSize(event.target.value)} />
            </Field>
            <Field label="Price">
              <Input
                type="number"
                step="0.01"
                min="0.01"
                value={variantPrice}
                onChange={(event) => setVariantPrice(event.target.value)}
                required
              />
            </Field>
            <Field label="Stock quantity">
              <Input
                type="number"
                min="0"
                value={stockQuantity}
                onChange={(event) => setStockQuantity(event.target.value)}
                required
              />
            </Field>
            <div className="flex items-end">
              <Button type="submit" disabled={isAddingVariant}>
                {isAddingVariant ? 'Adding…' : 'Add variant'}
              </Button>
            </div>
          </form>

          {error ? (
            <p className="text-sm text-danger" role="alert">
              {error}
            </p>
          ) : null}

          <DataTable
            columns={variantColumns}
            rows={variants}
            rowKey={(variant) => variant.id}
            rowClassName={(variant) =>
              variant.available_stock <= lowStockThreshold ? 'bg-warning-soft/20' : undefined
            }
            emptyTitle="No variants yet"
            emptyDescription="Add your first SKU above."
          />
        </CardBody>
      </Card>
    </HubPage>
  );
}
