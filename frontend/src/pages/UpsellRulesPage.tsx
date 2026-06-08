import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { ProductUpsellRule } from '../types/sprintD';

const DEFAULT_TEMPLATE =
  'You might also like {target_product_title} for {target_price} {currency}.';

const TEMPLATE_TOKENS = ['{target_product_title}', '{target_price}', '{currency}'] as const;

function previewUpsellTemplate(template: string, title: string, price: string, currency: string): string {
  return template
    .replace('{target_product_title}', title)
    .replace('{target_price}', price)
    .replace('{currency}', currency);
}

export function UpsellRulesPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const products = useQuery({
    queryKey: queryKeys.products(selectedShopId),
    queryFn: () => apiClient.listProducts(selectedShopId),
    enabled: Boolean(selectedShopId),
  });
  const rules = useQuery({
    queryKey: ['upsell-rules', selectedShopId],
    queryFn: () => apiClient.listProductUpsells(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const [sourceProductId, setSourceProductId] = useState('');
  const [targetProductId, setTargetProductId] = useState('');
  const [messageTemplate, setMessageTemplate] = useState(DEFAULT_TEMPLATE);
  const [deleteTarget, setDeleteTarget] = useState<ProductUpsellRule | null>(null);

  const targetOptions = useMemo(
    () => (products.data ?? []).filter((product) => product.id !== sourceProductId),
    [products.data, sourceProductId],
  );

  const sourceOptions = useMemo(
    () => (products.data ?? []).filter((product) => product.id !== targetProductId),
    [products.data, targetProductId],
  );

  useEffect(() => {
    if (!products.data?.length) {
      return;
    }

    const defaultSource = products.data[0].id;
    const defaultTarget = products.data.find((product) => product.id !== defaultSource)?.id ?? '';

    if (!sourceProductId) {
      setSourceProductId(defaultSource);
    }
    if (!targetProductId) {
      setTargetProductId(defaultTarget);
    }
  }, [products.data, sourceProductId, targetProductId]);

  useEffect(() => {
    if (!sourceProductId || !targetProductId || sourceProductId === targetProductId) {
      const fallback = (products.data ?? []).find((product) => product.id !== sourceProductId);
      if (fallback && fallback.id !== targetProductId) {
        setTargetProductId(fallback.id);
      }
    }
  }, [products.data, sourceProductId, targetProductId]);

  const sourceProduct = products.data?.find((product) => product.id === sourceProductId);
  const targetProduct = products.data?.find((product) => product.id === targetProductId);

  const activeCount = useMemo(
    () => (rules.data ?? []).filter((rule) => rule.is_active).length,
    [rules.data],
  );

  const create = useMutation({
    mutationFn: () =>
      apiClient.createProductUpsell(selectedShopId, {
        source_product_id: sourceProductId,
        target_product_id: targetProductId,
        message_template: messageTemplate.trim(),
        is_active: true,
      }),
    onSuccess: () => {
      showToast('Upsell rule created.', 'success');
      queryClient.invalidateQueries({ queryKey: ['upsell-rules', selectedShopId] });
    },
    onError: (error) =>
      showToast(error instanceof Error ? error.message : 'Failed to create upsell', 'error'),
  });

  const toggleActive = useMutation({
    mutationFn: ({ ruleId, isActive }: { ruleId: string; isActive: boolean }) =>
      apiClient.updateProductUpsell(selectedShopId, ruleId, { is_active: isActive }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['upsell-rules', selectedShopId] });
    },
    onError: (error) =>
      showToast(error instanceof Error ? error.message : 'Failed to update upsell', 'error'),
  });

  const remove = useMutation({
    mutationFn: (ruleId: string) => apiClient.deleteProductUpsell(selectedShopId, ruleId),
    onSuccess: () => {
      showToast('Upsell rule deleted.', 'success');
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ['upsell-rules', selectedShopId] });
    },
    onError: (error) =>
      showToast(error instanceof Error ? error.message : 'Failed to delete upsell', 'error'),
  });

  function appendToken(token: string) {
    setMessageTemplate((current) => (current.trim() ? `${current.trim()} ${token}` : token));
  }

  function resetForm() {
    setMessageTemplate(DEFAULT_TEMPLATE);
    if (products.data?.length) {
      setSourceProductId(products.data[0].id);
      const fallback = products.data.find((product) => product.id !== products.data![0].id);
      setTargetProductId(fallback?.id ?? '');
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!sourceProductId || !targetProductId) {
      showToast('Select source and target products.', 'error');
      return;
    }
    if (sourceProductId === targetProductId) {
      showToast('Source and target products must be different.', 'error');
      return;
    }
    create.mutate();
  }

  const productTitle = (id: string) =>
    products.data?.find((product) => product.id === id)?.title ?? `${id.slice(0, 8)}…`;

  const canSubmit = Boolean(
    selectedShopId &&
      sourceProductId &&
      targetProductId &&
      sourceProductId !== targetProductId &&
      !create.isPending,
  );

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Controlled upsell</p>
        <h1>Upsell rules</h1>
        <p>
          Suggest only pre-approved product pairs after the main order is clear. The agent never
          invents upsell items, prices, or discounts.
        </p>
        <ShopSelector />
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Create upsell rule</h2>
        <p className="analytics-toolbar__summary">
          When a customer orders the source product, the agent may append the configured upsell
          message. Upsells are skipped during handoff or low-confidence flows.
        </p>

        {!selectedShopId ? (
          <p className="empty-state">Select a shop to configure upsell rules.</p>
        ) : products.isLoading ? (
          <p className="loading-state">Loading products...</p>
        ) : (products.data?.length ?? 0) < 2 ? (
          <p className="empty-state">
            Add at least two products before creating upsell rules.{' '}
            <Link className="table-link" to="/products">
              Go to products
            </Link>
          </p>
        ) : (
          <form className="trigger-rules-form" onSubmit={submit}>
            <div className="rule-pair-flow">
              <label className="form-field">
                <span>Source product (main order)</span>
                <select
                  value={sourceProductId}
                  onChange={(event) => setSourceProductId(event.target.value)}
                  required
                >
                  <option value="">Select product</option>
                  {sourceOptions.map((product) => (
                    <option key={product.id} value={product.id}>
                      {product.title}
                    </option>
                  ))}
                </select>
              </label>

              <span className="rule-pair-flow__arrow" aria-hidden="true">
                →
              </span>

              <label className="form-field">
                <span>Target product (upsell)</span>
                <select
                  value={targetProductId}
                  onChange={(event) => setTargetProductId(event.target.value)}
                  required
                >
                  <option value="">Select product</option>
                  {targetOptions.map((product) => (
                    <option key={product.id} value={product.id}>
                      {product.title}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="form-field form-field--wide">
              <span>Message template</span>
              <textarea
                rows={3}
                value={messageTemplate}
                onChange={(event) => setMessageTemplate(event.target.value)}
                placeholder={DEFAULT_TEMPLATE}
                required
              />
            </label>

            <div className="form-field trigger-rules-form__examples">
              <span>Insert template variables</span>
              <div className="filter-chips" role="group" aria-label="Template variables">
                {TEMPLATE_TOKENS.map((token) => (
                  <button
                    key={token}
                    type="button"
                    className="filter-chip"
                    onClick={() => appendToken(token)}
                  >
                    {token}
                  </button>
                ))}
              </div>
            </div>

            {targetProduct ? (
              <div className="form-field form-field--wide">
                <span>Preview</span>
                <p className="template-preview">
                  {previewUpsellTemplate(
                    messageTemplate.trim() || DEFAULT_TEMPLATE,
                    targetProduct.title,
                    String(targetProduct.base_price ?? '0'),
                    targetProduct.currency,
                  )}
                </p>
              </div>
            ) : null}

            <div className="button-row">
              <button className="button button--primary" type="submit" disabled={!canSubmit}>
                {create.isPending ? 'Creating…' : 'Create upsell rule'}
              </button>
              <button className="button button--ghost-dark" type="button" onClick={resetForm}>
                Reset form
              </button>
            </div>
          </form>
        )}

        {create.error ? (
          <p className="form-error">
            {create.error instanceof Error ? create.error.message : 'Failed to create upsell'}
          </p>
        ) : null}
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header">
          <div>
            <h2>Configured upsells</h2>
            <p className="analytics-toolbar__summary">
              {activeCount} active · {(rules.data?.length ?? 0) - activeCount} paused
            </p>
          </div>
        </div>

        {rules.isLoading ? <p className="loading-state">Loading upsell rules...</p> : null}
        {rules.error ? (
          <p className="form-error">
            {rules.error instanceof Error ? rules.error.message : 'Failed to load upsell rules'}
          </p>
        ) : null}

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Target</th>
                <th>Template</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.data?.map((rule) => (
                <tr key={rule.id}>
                  <td>
                    <Link className="table-link" to={`/products/${rule.source_product_id}`}>
                      {productTitle(rule.source_product_id)}
                    </Link>
                  </td>
                  <td>
                    <Link className="table-link" to={`/products/${rule.target_product_id}`}>
                      {productTitle(rule.target_product_id)}
                    </Link>
                  </td>
                  <td>
                    <p>{rule.message_template ?? DEFAULT_TEMPLATE}</p>
                  </td>
                  <td>
                    <span className="status-pill">{rule.is_active ? 'Active' : 'Paused'}</span>
                  </td>
                  <td>
                    <div className="rule-actions">
                      <button
                        className="button button--ghost"
                        type="button"
                        disabled={toggleActive.isPending}
                        onClick={() =>
                          toggleActive.mutate({ ruleId: rule.id, isActive: !rule.is_active })
                        }
                      >
                        {rule.is_active ? 'Pause' : 'Activate'}
                      </button>
                      <button
                        className="button button--ghost"
                        type="button"
                        onClick={() => setDeleteTarget(rule)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rules.isLoading && (rules.data?.length ?? 0) === 0 ? (
            <p className="empty-state">No upsell rules yet. Create one above.</p>
          ) : null}
        </div>
      </section>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete upsell rule?"
        message="The agent will stop suggesting this product pair in conversations."
        confirmLabel="Delete rule"
        onConfirm={() => deleteTarget && remove.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
        isLoading={remove.isPending}
      />
    </div>
  );
}
