import { FormEvent, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { useShop } from '../contexts/ShopContext';
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

  useEffect(() => {
    if (!shopId || !productId) {
      return;
    }

    apiClient
      .getProduct(shopId, productId)
      .then((data) => {
        setProduct(data);
        setTitle(data.title);
        setDescription(data.description ?? '');
        setBasePrice(data.base_price);
        setStatus(data.status);
      })
      .catch(() => setProduct(null));

    apiClient
      .listVariants(shopId, productId)
      .then(setVariants)
      .catch(() => setVariants([]));
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

  if (!shopId) {
    return (
      <div className="page-stack">
        <section className="dashboard-card">
          <p className="empty-state">Open this product from the products list.</p>
          <Link className="table-link" to="/products">
            Back to products
          </Link>
        </section>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="page-stack">
        <section className="dashboard-card">
          <p className="loading-state">Loading product...</p>
        </section>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <section className="dashboard-card">
        <p className="dashboard-card__eyebrow">Product</p>
        <h1>{product.title}</h1>
        <Link className="table-link" to="/products">
          Back to products
        </Link>

        <form className="inline-form" onSubmit={handleUpdateProduct}>
          <label className="form-field">
            <span>Title</span>
            <input value={title} onChange={(event) => setTitle(event.target.value)} required />
          </label>
          <label className="form-field">
            <span>Description</span>
            <input value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <label className="form-field">
            <span>Base price</span>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={basePrice}
              onChange={(event) => setBasePrice(event.target.value)}
              required
            />
          </label>
          <label className="form-field">
            <span>Status</span>
            <select value={status} onChange={(event) => setStatus(event.target.value as Product['status'])}>
              <option value="active">active</option>
              <option value="inactive">inactive</option>
              <option value="archived">archived</option>
            </select>
          </label>
          <button className="button button--primary" type="submit" disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save product'}
          </button>
        </form>
      </section>

      <section className="dashboard-card">
        <p className="dashboard-card__eyebrow">Variants &amp; inventory</p>
        <h2>Variants</h2>

        <form className="inline-form" onSubmit={handleAddVariant}>
          <label className="form-field">
            <span>SKU</span>
            <input value={sku} onChange={(event) => setSku(event.target.value)} required />
          </label>
          <label className="form-field">
            <span>Color</span>
            <input value={color} onChange={(event) => setColor(event.target.value)} />
          </label>
          <label className="form-field">
            <span>Size</span>
            <input value={size} onChange={(event) => setSize(event.target.value)} />
          </label>
          <label className="form-field">
            <span>Price</span>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={variantPrice}
              onChange={(event) => setVariantPrice(event.target.value)}
              required
            />
          </label>
          <label className="form-field">
            <span>Stock quantity</span>
            <input
              type="number"
              min="0"
              value={stockQuantity}
              onChange={(event) => setStockQuantity(event.target.value)}
              required
            />
          </label>
          <button className="button button--primary" type="submit" disabled={isAddingVariant}>
            {isAddingVariant ? 'Adding...' : 'Add variant'}
          </button>
        </form>
        {error ? <p className="form-error">{error}</p> : null}

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Color</th>
                <th>Size</th>
                <th>Price</th>
                <th>Stock</th>
                <th>Reserved</th>
                <th>Available</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {variants.map((variant) => (
                <tr
                  key={variant.id}
                  className={variant.available_stock <= lowStockThreshold ? 'row-warning' : undefined}
                >
                  <td>{variant.sku}</td>
                  <td>{variant.color ?? '—'}</td>
                  <td>{variant.size ?? '—'}</td>
                  <td>{variant.price}</td>
                  <td>{variant.stock_quantity}</td>
                  <td>{variant.reserved_quantity}</td>
                  <td>
                    {variant.available_stock}
                    {variant.available_stock <= lowStockThreshold ? ' ⚠' : ''}
                  </td>
                  <td>{variant.is_active ? 'yes' : 'no'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {variants.length === 0 ? <p className="empty-state">No variants yet.</p> : null}
        </div>
      </section>
    </div>
  );
}
