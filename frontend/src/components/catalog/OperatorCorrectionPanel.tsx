import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import { useToast } from '../../contexts/ToastContext';
import { apiClient } from '../../services/apiClient';
import type { ResolveProductResponse, ResolveVariantResponse, ResolverTrace } from '../../types/resolve';

export function OperatorCorrectionPanel({
  shopId,
  trace,
  productResult,
  variantResult,
}: {
  shopId: string;
  trace: ResolverTrace;
  productResult: ResolveProductResponse | null;
  variantResult: ResolveVariantResponse | null;
}) {
  const { showToast } = useToast();
  const [notes, setNotes] = useState('');

  const feedbackMutation = useMutation({
    mutationFn: (action: 'accept_ai' | 'correct_product' | 'correct_variant' | 'taxonomy_issue') =>
      apiClient.submitResolverFeedback(shopId, trace.id, {
        action,
        original_product_id: productResult?.candidates[0]?.product_id,
        corrected_product_id: productResult?.candidates[1]?.product_id,
        original_variant_id: variantResult?.candidates[0]?.variant_id,
        corrected_variant_id: variantResult?.candidates[1]?.variant_id,
        notes: notes || undefined,
      }),
    onSuccess: () => showToast('Feedback saved', 'success'),
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const isPending = feedbackMutation.isPending;

  return (
    <div className="cc-correction">
      <h3 className="cc-subhead">Operator correction</h3>
      <p className="cc-card__hint">Review the AI decision and record operator feedback.</p>
      <div className="cc-field">
        <label className="cc-field-label" htmlFor="correction-notes">
          Notes / corrected alias hint
        </label>
        <textarea
          id="correction-notes"
          className="cc-textarea"
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Optional context for this correction…"
        />
      </div>
      <div className="cc-correction__actions">
        <button
          className="button button--primary"
          type="button"
          disabled={isPending}
          onClick={() => feedbackMutation.mutate('accept_ai')}
        >
          Accept AI choice
        </button>
        <button
          className="button button--secondary"
          type="button"
          disabled={isPending}
          onClick={() => feedbackMutation.mutate('correct_product')}
        >
          Correct product
        </button>
        <button
          className="button button--secondary"
          type="button"
          disabled={isPending}
          onClick={() => feedbackMutation.mutate('correct_variant')}
        >
          Correct variant
        </button>
        <button
          className="button button--ghost-dark"
          type="button"
          disabled={isPending}
          onClick={() => feedbackMutation.mutate('taxonomy_issue')}
        >
          Mark taxonomy issue
        </button>
      </div>
    </div>
  );
}
