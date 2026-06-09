import { FormEvent, useState } from 'react';
import { useMutation } from '@tanstack/react-query';

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
    <div className="cc-alias-editor">
      <div className="cc-alias-editor__head">
        <h3 className="cc-subhead">Aliases</h3>
        <span className="cc-card__hint">{product.normalized_title}</span>
      </div>
      {product.aliases.length === 0 ? (
        <p className="cc-card__footnote">No aliases yet — add Persian/English synonyms below.</p>
      ) : (
        <ul className="cc-alias-list">
          {product.aliases.map((alias) => (
            <li key={alias.id} className="cc-alias-chip" dir="auto">
              <span className="cc-alias-chip__text">{alias.alias_text}</span>
              <button
                type="button"
                className="cc-alias-chip__remove"
                aria-label={`Remove alias ${alias.alias_text}`}
                onClick={() => patchMutation.mutate({ remove: [alias.alias_text] })}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <form className="cc-alias-form" onSubmit={handleAdd}>
        <input
          className="cc-alias-form__input"
          value={newAlias}
          onChange={(e) => setNewAlias(e.target.value)}
          placeholder="Add Persian/English alias"
          aria-label="New alias"
          dir="auto"
        />
        <button className="button button--secondary" type="submit" disabled={patchMutation.isPending || !newAlias.trim()}>
          {patchMutation.isPending ? 'Saving…' : 'Add'}
        </button>
      </form>
    </div>
  );
}
