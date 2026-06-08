import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
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
    <form className="alias-form" onSubmit={onSubmit}>
      <div className="filter-grid">
        <label className="form-field">
          <span>{rawLabel}</span>
          <input
            value={rawValue}
            onChange={(event) => onRawChange(event.target.value)}
            placeholder={type === 'color' ? 'مشکی' : 'فری سایز'}
            dir="auto"
            required
          />
        </label>
        <label className="form-field">
          <span>{normalizedLabel}</span>
          <input
            value={normalizedValue}
            onChange={(event) => onNormalizedChange(event.target.value)}
            placeholder={type === 'color' ? 'black' : 'FREE'}
            required
          />
        </label>
      </div>

      <div className="form-field alias-form__examples">
        <span>Quick examples</span>
        <div className="filter-chips" role="group" aria-label={`${type} alias examples`}>
          {examples.map((example) => (
            <button
              key={`${example.raw}-${example.normalized}`}
              type="button"
              className="filter-chip"
              onClick={() => {
                onRawChange(example.raw);
                onNormalizedChange(example.normalized);
              }}
            >
              {example.raw} → {example.normalized}
            </button>
          ))}
        </div>
      </div>

      <div className="button-row">
        <button className="button button--primary" type="submit" disabled={disabled || isPending}>
          {isPending ? 'Adding…' : submitLabel}
        </button>
      </div>
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
  if (isLoading) {
    return <p className="loading-state">Loading {type} aliases...</p>;
  }

  if (error) {
    return <p className="form-error">{error.message}</p>;
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Raw value</th>
            <th>Normalized</th>
            <th>{type === 'color' ? 'Scope' : 'Category'}</th>
          </tr>
        </thead>
        <tbody>
          {rows?.map((alias) => (
            <tr key={alias.id}>
              <td>{alias.raw_value}</td>
              <td>{alias.normalized_value}</td>
              <td>
                {type === 'color'
                  ? alias.shop_id
                    ? 'Shop'
                    : 'Global'
                  : ((alias as SizeAlias).category ?? 'Any category')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {(rows?.length ?? 0) === 0 ? (
        <p className="empty-state">No {type} aliases yet. Add one above.</p>
      ) : null}
    </div>
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
    if (shopId) {
      createColor.mutate();
    }
  }

  function submitSize(event: FormEvent) {
    event.preventDefault();
    if (shopId) {
      createSize.mutate();
    }
  }

  const formDisabled = !shopId;

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Sprint A tooling</p>
        <h1>Fashion dictionary</h1>
        <p>
          Manage deterministic color and size aliases used by the variant resolver. Shop-specific
          aliases override global defaults.
        </p>
        <ShopSelector />
      </section>

      {!shopId ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="empty-state">Select a shop to manage fashion aliases.</p>
        </section>
      ) : (
        <div className="dashboard-grid">
          <section className="dashboard-card">
            <h2>Color aliases</h2>
            <p className="analytics-toolbar__summary">
              Map customer color words (including Persian) to a canonical color value.
            </p>
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
          </section>

          <section className="dashboard-card">
            <h2>Size aliases</h2>
            <p className="analytics-toolbar__summary">
              Normalize size phrases like free size or medium into standard variant sizes.
            </p>
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
          </section>
        </div>
      )}
    </div>
  );
}
