import { FormEvent, useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import { Button, Input } from '../ui';
import { useToast } from '../../contexts/ToastContext';
import { apiClient } from '../../services/apiClient';
import type { ProductNormalized } from '../../types/catalog';

export function AliasEditor({
  shopId,
  product,
  onUpdated,
}: {
  shopId: string;
  product: ProductNormalized;
  onUpdated: () => void;
}) {
  const { showToast } = useToast();
  const [newAlias, setNewAlias] = useState('');

  const patchMutation = useMutation({
    mutationFn: (payload: { add?: string[]; remove?: string[] }) =>
      apiClient.patchProductAliases(shopId, product.product_id, payload),
    onSuccess: () => {
      showToast('Aliases updated', 'success');
      setNewAlias('');
      onUpdated();
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  function handleAdd(event: FormEvent) {
    event.preventDefault();
    if (!newAlias.trim()) return;
    patchMutation.mutate({ add: [newAlias.trim()] });
  }

  return (
    <div className="flex flex-col gap-3">
      <div>
        <h3 className="text-sm font-semibold text-fg">Aliases</h3>
        <p className="text-xs text-muted">{product.normalized_title}</p>
      </div>
      {product.aliases.length === 0 ? (
        <p className="text-xs text-muted">No aliases yet — add Persian/English synonyms below.</p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {product.aliases.map((alias) => (
            <li
              key={alias.id}
              className="inline-flex items-center gap-1 rounded-full border border-border bg-surface-sunken px-2 py-1 text-sm"
              dir="auto"
            >
              <span>{alias.alias_text}</span>
              <button
                type="button"
                className="rounded px-1 text-muted hover:bg-surface hover:text-danger"
                aria-label={`Remove alias ${alias.alias_text}`}
                onClick={() => patchMutation.mutate({ remove: [alias.alias_text] })}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <form className="flex flex-wrap gap-2" onSubmit={handleAdd}>
        <Input
          value={newAlias}
          onChange={(e) => setNewAlias(e.target.value)}
          placeholder="Add Persian/English alias"
          aria-label="New alias"
          dir="auto"
          className="min-w-[12rem] flex-1"
        />
        <Button type="submit" variant="secondary" size="sm" disabled={patchMutation.isPending || !newAlias.trim()}>
          {patchMutation.isPending ? 'Saving…' : 'Add'}
        </Button>
      </form>
    </div>
  );
}
