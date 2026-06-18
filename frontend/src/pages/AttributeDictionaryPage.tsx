import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { HubPage } from '../components/shell/HubPage';
import { Button, Card, CardBody, CardHeader, Field, Input } from '../components/ui';
import { DataTable, EmptyState } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import type { AttributeAlias } from '../types/fashion';

const EXAMPLES = [
  { attribute_slug: 'color', raw_value: 'مشکی', normalized_value: 'black' },
  { attribute_slug: 'size', raw_value: 'لارج', normalized_value: 'L' },
  { attribute_slug: 'storage', raw_value: '۱۲۸ گیگ', normalized_value: '128GB' },
  { attribute_slug: 'warranty', raw_value: 'گارانتی دار', normalized_value: 'with_warranty' },
  { attribute_slug: 'shade', raw_value: 'شماره ۲', normalized_value: 'shade_2' },
  { attribute_slug: 'brand', raw_value: 'بوش', normalized_value: 'Bosch' },
  { attribute_slug: 'voltage', raw_value: '۲۲۰ ولت', normalized_value: '220V' },
  { attribute_slug: 'license_type', raw_value: 'سالانه', normalized_value: 'annual' },
] as const;

export function AttributeDictionaryPage() {
  const { selectedShop } = useShop();
  const shopId = selectedShop?.id;
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [attributeSlug, setAttributeSlug] = useState('color');
  const [rawValue, setRawValue] = useState('');
  const [normalizedValue, setNormalizedValue] = useState('');

  const aliases = useQuery({
    queryKey: ['attribute-aliases', shopId],
    queryFn: () => apiClient.listAttributeAliases(shopId!),
    enabled: Boolean(shopId),
  });
  const createAlias = useMutation({
    mutationFn: () => apiClient.createAttributeAlias(shopId!, {
      attribute_slug: attributeSlug,
      raw_value: rawValue,
      normalized_value: normalizedValue,
      language: 'und',
    }),
    onSuccess: () => {
      setRawValue('');
      setNormalizedValue('');
      showToast('Attribute alias added.', 'success');
      queryClient.invalidateQueries({ queryKey: ['attribute-aliases', shopId] });
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to add attribute alias', 'error'),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (shopId) createAlias.mutate();
  }

  const columns: Column<AttributeAlias>[] = [
    { key: 'attribute', header: 'Attribute', render: (alias) => alias.attribute_slug },
    { key: 'raw', header: 'Customer value', render: (alias) => alias.raw_value },
    { key: 'normalized', header: 'Canonical value', render: (alias) => alias.normalized_value },
    { key: 'scope', header: 'Scope', render: (alias) => alias.shop_id ? 'Shop' : 'System' },
  ];

  return (
    <HubPage
      eyebrow="Catalog"
      title="Attribute dictionary"
      description="Normalize customer language for any catalog attribute. Color and size are standard attributes alongside storage, warranty, shade, brand, voltage, and license type."
    >
      {!shopId ? (
        <Card><CardBody><EmptyState title="Select a shop" description="Use the shop switcher in the top bar to manage aliases." /></CardBody></Card>
      ) : (
        <Card>
          <CardHeader title="Attribute aliases" description="Map customer wording to canonical catalog values used by search and variant resolution." />
          <CardBody className="flex flex-col gap-6">
            <form className="flex flex-col gap-4" onSubmit={submit}>
              <div className="grid gap-3 md:grid-cols-3">
                <Field label="Attribute"><Input value={attributeSlug} onChange={(event) => setAttributeSlug(event.target.value)} placeholder="storage" required /></Field>
                <Field label="Customer value"><Input value={rawValue} onChange={(event) => setRawValue(event.target.value)} placeholder="۱۲۸ گیگ" dir="auto" required /></Field>
                <Field label="Canonical value"><Input value={normalizedValue} onChange={(event) => setNormalizedValue(event.target.value)} placeholder="128GB" required /></Field>
              </div>
              <Field label="Quick examples">
                <div className="flex flex-wrap gap-2">
                  {EXAMPLES.map((example) => (
                    <button key={example.attribute_slug} type="button" className="rounded-full border border-border px-3 py-1 text-xs text-muted hover:text-fg" onClick={() => {
                      setAttributeSlug(example.attribute_slug); setRawValue(example.raw_value); setNormalizedValue(example.normalized_value);
                    }}>
                      {example.attribute_slug}: {example.raw_value} → {example.normalized_value}
                    </button>
                  ))}
                </div>
              </Field>
              <Button type="submit" disabled={createAlias.isPending}>{createAlias.isPending ? 'Adding…' : 'Add attribute alias'}</Button>
            </form>
            <DataTable columns={columns} rows={aliases.data ?? []} rowKey={(alias) => alias.id} isLoading={aliases.isLoading} error={aliases.error instanceof Error ? aliases.error.message : null} emptyTitle="No attribute aliases yet" emptyDescription="Add one using the form above." />
          </CardBody>
        </Card>
      )}
    </HubPage>
  );
}
