import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input, Select } from '../components/ui';
import { DataTable, EmptyState, LoadingState } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { cn } from '../lib/cn';
import { apiClient } from '../services/apiClient';
import type { ProductUpsellRule } from '../types/sprintD';

const DEFAULT_TEMPLATE = 'You might also like {target_product_title} for {target_price} {currency}.';
const TEMPLATE_TOKENS = ['{target_product_title}', '{target_price}', '{currency}'] as const;

function previewUpsellTemplate(template: string, title: string, price: string, currency: string): string {
  return template
    .replace('{target_product_title}', title)
    .replace('{target_price}', price)
    .replace('{currency}', currency);
}

function Chip({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted transition-colors hover:text-fg"
    >
      {children}
    </button>
  );
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
    if (!products.data?.length) return;
    const defaultSource = products.data[0].id;
    const defaultTarget = products.data.find((product) => product.id !== defaultSource)?.id ?? '';
    if (!sourceProductId) setSourceProductId(defaultSource);
    if (!targetProductId) setTargetProductId(defaultTarget);
  }, [products.data, sourceProductId, targetProductId]);

  useEffect(() => {
    if (!sourceProductId || !targetProductId || sourceProductId === targetProductId) {
      const fallback = (products.data ?? []).find((product) => product.id !== sourceProductId);
      if (fallback && fallback.id !== targetProductId) setTargetProductId(fallback.id);
    }
  }, [products.data, sourceProductId, targetProductId]);

  const targetProduct = products.data?.find((product) => product.id === targetProductId);
  const activeCount = useMemo(() => (rules.data ?? []).filter((rule) => rule.is_active).length, [rules.data]);

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
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to create upsell', 'error'),
  });

  const toggleActive = useMutation({
    mutationFn: ({ ruleId, isActive }: { ruleId: string; isActive: boolean }) =>
      apiClient.updateProductUpsell(selectedShopId, ruleId, { is_active: isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['upsell-rules', selectedShopId] }),
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to update upsell', 'error'),
  });

  const remove = useMutation({
    mutationFn: (ruleId: string) => apiClient.deleteProductUpsell(selectedShopId, ruleId),
    onSuccess: () => {
      showToast('Upsell rule deleted.', 'success');
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ['upsell-rules', selectedShopId] });
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to delete upsell', 'error'),
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
    selectedShopId && sourceProductId && targetProductId && sourceProductId !== targetProductId && !create.isPending,
  );

  const columns: Column<ProductUpsellRule>[] = [
    {
      key: 'source',
      header: 'Source',
      render: (rule) => (
        <Link className="text-accent hover:underline" to={`/catalog/products/${rule.source_product_id}`}>
          {productTitle(rule.source_product_id)}
        </Link>
      ),
    },
    {
      key: 'target',
      header: 'Target',
      render: (rule) => (
        <Link className="text-accent hover:underline" to={`/catalog/products/${rule.target_product_id}`}>
          {productTitle(rule.target_product_id)}
        </Link>
      ),
    },
    {
      key: 'template',
      header: 'Template',
      className: 'hidden md:table-cell',
      render: (rule) => <span className="text-sm">{rule.message_template ?? DEFAULT_TEMPLATE}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (rule) => <Badge tone={rule.is_active ? 'success' : 'neutral'}>{rule.is_active ? 'Active' : 'Paused'}</Badge>,
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (rule) => (
        <div className="flex justify-end gap-1">
          <Button
            variant="ghost"
            size="sm"
            type="button"
            disabled={toggleActive.isPending}
            onClick={() => toggleActive.mutate({ ruleId: rule.id, isActive: !rule.is_active })}
          >
            {rule.is_active ? 'Pause' : 'Activate'}
          </Button>
          <Button variant="ghost" size="sm" type="button" onClick={() => setDeleteTarget(rule)}>
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <HubPage
      eyebrow="Automation"
      title="Upsell rules"
      description="Suggest only pre-approved product pairs after the main order is clear."
    >
      <Card>
        <CardHeader title="Create upsell rule" description="Upsells are skipped during handoff or low-confidence flows." />
        <CardBody>
          {!selectedShopId ? (
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          ) : products.isLoading ? (
            <LoadingState label="Loading products…" />
          ) : (products.data?.length ?? 0) < 2 ? (
            <EmptyState
              title="Need at least two products"
              description={
                <>
                  Add more products before creating upsell rules.{' '}
                  <Link className="text-accent hover:underline" to="/catalog/products">
                    Go to products
                  </Link>
                </>
              }
            />
          ) : (
            <form className="flex flex-col gap-4" onSubmit={submit}>
              <div className="grid gap-3 sm:grid-cols-[1fr_auto_1fr] sm:items-end">
                <Field label="Source product (main order)">
                  <Select value={sourceProductId} onChange={(e) => setSourceProductId(e.target.value)} required>
                    <option value="">Select product</option>
                    {sourceOptions.map((product) => (
                      <option key={product.id} value={product.id}>{product.title}</option>
                    ))}
                  </Select>
                </Field>
                <span className="hidden pb-2 text-center text-muted sm:block" aria-hidden="true">→</span>
                <Field label="Target product (upsell)">
                  <Select value={targetProductId} onChange={(e) => setTargetProductId(e.target.value)} required>
                    <option value="">Select product</option>
                    {targetOptions.map((product) => (
                      <option key={product.id} value={product.id}>{product.title}</option>
                    ))}
                  </Select>
                </Field>
              </div>

              <Field label="Message template">
                <textarea
                  rows={3}
                  value={messageTemplate}
                  onChange={(e) => setMessageTemplate(e.target.value)}
                  placeholder={DEFAULT_TEMPLATE}
                  required
                  className="w-full resize-y rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg focus:border-accent focus:outline-none"
                />
              </Field>

              <Field label="Insert template variables">
                <div className="flex flex-wrap gap-2" role="group" aria-label="Template variables">
                  {TEMPLATE_TOKENS.map((token) => (
                    <Chip key={token} onClick={() => appendToken(token)}>{token}</Chip>
                  ))}
                </div>
              </Field>

              {targetProduct ? (
                <Field label="Preview">
                  <p className="rounded-lg border border-border bg-surface-sunken px-3 py-2 text-sm text-fg">
                    {previewUpsellTemplate(
                      messageTemplate.trim() || DEFAULT_TEMPLATE,
                      targetProduct.title,
                      String(targetProduct.base_price ?? '0'),
                      targetProduct.currency,
                    )}
                  </p>
                </Field>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={!canSubmit}>
                  {create.isPending ? 'Creating…' : 'Create upsell rule'}
                </Button>
                <Button type="button" variant="secondary" onClick={resetForm}>Reset form</Button>
              </div>

              {create.error ? (
                <p className="text-sm text-danger">
                  {create.error instanceof Error ? create.error.message : 'Failed to create upsell'}
                </p>
              ) : null}
            </form>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Configured upsells"
          description={`${activeCount} active · ${(rules.data?.length ?? 0) - activeCount} paused`}
        />
        <DataTable
          columns={columns}
          rows={rules.data ?? []}
          rowKey={(rule) => rule.id}
          isLoading={rules.isLoading}
          error={rules.error instanceof Error ? rules.error.message : null}
          emptyTitle="No upsell rules yet"
        />
      </Card>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete upsell rule?"
        message="The agent will stop suggesting this product pair in conversations."
        confirmLabel="Delete rule"
        onConfirm={() => deleteTarget && remove.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
        isLoading={remove.isPending}
      />
    </HubPage>
  );
}
