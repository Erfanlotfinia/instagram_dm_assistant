import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { HubPage } from '../components/shell/HubPage';
import { Button, Card, CardBody, CardHeader, Field, Input } from '../components/ui';
import { DataTable, EmptyState } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { cn } from '../lib/cn';
import { apiClient } from '../services/apiClient';
import type { ColorAlias, SizeAlias } from '../types/fashion';

const COLOR_EXAMPLES = [
  { raw: 'مشکی', normalized: 'black' },
  { raw: 'سیاه', normalized: 'black' },
  { raw: 'قرمز', normalized: 'red' },
  { raw: 'navy', normalized: 'navy' },
] as const;

const SIZE_EXAMPLES = [
  { raw: 'فری سایز', normalized: 'FREE' },
  { raw: 'L', normalized: 'L' },
  { raw: 'XL', normalized: 'XL' },
  { raw: 'medium', normalized: 'M' },
] as const;

function Chip({
  active,
  onClick,
  children,
}: {
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
        active ? 'border-accent bg-accent-soft text-accent' : 'border-border bg-surface text-muted hover:text-fg',
      )}
    >
      {children}
    </button>
  );
}

interface AliasFormProps {
  type: 'color' | 'size';
  rawValue: string;
  normalizedValue: string;
  onRawChange: (value: string) => void;
  onNormalizedChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  isPending: boolean;
  disabled: boolean;
  examples: readonly { raw: string; normalized: string }[];
}

function AliasForm({
  type,
  rawValue,
  normalizedValue,
  onRawChange,
  onNormalizedChange,
  onSubmit,
  isPending,
  disabled,
  examples,
}: AliasFormProps) {
  const rawLabel = type === 'color' ? 'Raw color (customer text)' : 'Raw size (customer text)';
  const normalizedLabel = type === 'color' ? 'Normalized color' : 'Normalized size';
  const submitLabel = type === 'color' ? 'Add color alias' : 'Add size alias';

  return (
    <form className="flex flex-col gap-4" onSubmit={onSubmit}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label={rawLabel}>
          <Input
            value={rawValue}
            onChange={(event) => onRawChange(event.target.value)}
            placeholder={type === 'color' ? 'مشکی' : 'فری سایز'}
            dir="auto"
            required
          />
        </Field>
        <Field label={normalizedLabel}>
          <Input
            value={normalizedValue}
            onChange={(event) => onNormalizedChange(event.target.value)}
            placeholder={type === 'color' ? 'black' : 'FREE'}
            required
          />
        </Field>
      </div>

      <Field label="Quick examples">
        <div className="flex flex-wrap gap-2" role="group" aria-label={`${type} alias examples`}>
          {examples.map((example) => (
            <Chip
              key={`${example.raw}-${example.normalized}`}
              onClick={() => {
                onRawChange(example.raw);
                onNormalizedChange(example.normalized);
              }}
            >
              {example.raw} → {example.normalized}
            </Chip>
          ))}
        </div>
      </Field>

      <Button type="submit" disabled={disabled || isPending}>
        {isPending ? 'Adding…' : submitLabel}
      </Button>
    </form>
  );
}

function AliasTable<T extends ColorAlias | SizeAlias>({
  rows,
  type,
  isLoading,
  error,
}: {
  rows: T[] | undefined;
  type: 'color' | 'size';
  isLoading: boolean;
  error: Error | null;
}) {
  const columns: Column<T>[] = [
    { key: 'raw', header: 'Raw value', render: (alias) => alias.raw_value },
    { key: 'normalized', header: 'Normalized', render: (alias) => alias.normalized_value },
    {
      key: 'scope',
      header: type === 'color' ? 'Scope' : 'Category',
      render: (alias) =>
        type === 'color'
          ? alias.shop_id
            ? 'Shop'
            : 'Global'
          : ((alias as SizeAlias).category ?? 'Any category'),
    },
  ];

  return (
    <DataTable
      columns={columns}
      rows={rows ?? []}
      rowKey={(alias) => alias.id}
      isLoading={isLoading}
      error={error?.message ?? null}
      emptyTitle={`No ${type} aliases yet`}
      emptyDescription="Add one using the form above."
    />
  );
}

export function FashionDictionaryPage() {
  const { selectedShop } = useShop();
  const shopId = selectedShop?.id;
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const colors = useQuery({
    queryKey: ['color-aliases', shopId],
    queryFn: () => apiClient.listColorAliases(shopId!),
    enabled: Boolean(shopId),
  });
  const sizes = useQuery({
    queryKey: ['size-aliases', shopId],
    queryFn: () => apiClient.listSizeAliases(shopId!),
    enabled: Boolean(shopId),
  });

  const [colorRaw, setColorRaw] = useState('');
  const [colorNormalized, setColorNormalized] = useState('');
  const [sizeRaw, setSizeRaw] = useState('');
  const [sizeNormalized, setSizeNormalized] = useState('');

  const createColor = useMutation({
    mutationFn: () =>
      apiClient.createColorAlias(shopId!, {
        raw_value: colorRaw,
        normalized_value: colorNormalized,
        language: 'und',
      }),
    onSuccess: () => {
      setColorRaw('');
      setColorNormalized('');
      showToast('Color alias added.', 'success');
      queryClient.invalidateQueries({ queryKey: ['color-aliases', shopId] });
    },
    onError: (error) =>
      showToast(error instanceof Error ? error.message : 'Failed to add color alias', 'error'),
  });

  const createSize = useMutation({
    mutationFn: () =>
      apiClient.createSizeAlias(shopId!, {
        raw_value: sizeRaw,
        normalized_value: sizeNormalized,
        category: null,
      }),
    onSuccess: () => {
      setSizeRaw('');
      setSizeNormalized('');
      showToast('Size alias added.', 'success');
      queryClient.invalidateQueries({ queryKey: ['size-aliases', shopId] });
    },
    onError: (error) =>
      showToast(error instanceof Error ? error.message : 'Failed to add size alias', 'error'),
  });

  function submitColor(event: FormEvent) {
    event.preventDefault();
    if (shopId) createColor.mutate();
  }

  function submitSize(event: FormEvent) {
    event.preventDefault();
    if (shopId) createSize.mutate();
  }

  const formDisabled = !shopId;

  return (
    <HubPage
      eyebrow="Catalog"
      title="Fashion dictionary"
      description="Manage color and size aliases for the variant resolver. Shop-specific aliases override global defaults."
    >
      {!shopId ? (
        <Card>
          <CardBody>
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar to manage aliases." />
          </CardBody>
        </Card>
      ) : (
        <div className="grid gap-5 lg:grid-cols-2">
          <Card>
            <CardHeader
              title="Color aliases"
              description="Map customer color words (including Persian) to a canonical color value."
            />
            <CardBody className="flex flex-col gap-5">
              <AliasForm
                type="color"
                rawValue={colorRaw}
                normalizedValue={colorNormalized}
                onRawChange={setColorRaw}
                onNormalizedChange={setColorNormalized}
                onSubmit={submitColor}
                isPending={createColor.isPending}
                disabled={formDisabled}
                examples={COLOR_EXAMPLES}
              />
              <AliasTable
                rows={colors.data}
                type="color"
                isLoading={colors.isLoading}
                error={colors.error instanceof Error ? colors.error : null}
              />
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Size aliases"
              description="Normalize size phrases like free size or medium into standard variant sizes."
            />
            <CardBody className="flex flex-col gap-5">
              <AliasForm
                type="size"
                rawValue={sizeRaw}
                normalizedValue={sizeNormalized}
                onRawChange={setSizeRaw}
                onNormalizedChange={setSizeNormalized}
                onSubmit={submitSize}
                isPending={createSize.isPending}
                disabled={formDisabled}
                examples={SIZE_EXAMPLES}
              />
              <AliasTable
                rows={sizes.data}
                type="size"
                isLoading={sizes.isLoading}
                error={sizes.error instanceof Error ? sizes.error : null}
              />
            </CardBody>
          </Card>
        </div>
      )}
    </HubPage>
  );
}
