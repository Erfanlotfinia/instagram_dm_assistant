import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import { Button, Field } from '../ui';
import { useToast } from '../../contexts/ToastContext';
import { apiClient } from '../../services/apiClient';
import type { ResolveProductResponse, ResolveVariantResponse, ResolverTrace } from '../../types/resolve';
import { cn } from '../../lib/cn';

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
    <div className="flex flex-col gap-3">
      <div>
        <h3 className="text-sm font-semibold text-fg">Operator correction</h3>
        <p className="text-xs text-muted">Review the AI decision and record operator feedback.</p>
      </div>
      <Field label="Notes / corrected alias hint" htmlFor="correction-notes">
        <textarea
          id="correction-notes"
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Optional context for this correction…"
          className={cn(
            'w-full resize-y rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg',
            'placeholder:text-subtle focus:border-accent focus:outline-none',
          )}
        />
      </Field>
      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" disabled={isPending} onClick={() => feedbackMutation.mutate('accept_ai')}>
          Accept AI choice
        </Button>
        <Button type="button" variant="secondary" size="sm" disabled={isPending} onClick={() => feedbackMutation.mutate('correct_product')}>
          Correct product
        </Button>
        <Button type="button" variant="secondary" size="sm" disabled={isPending} onClick={() => feedbackMutation.mutate('correct_variant')}>
          Correct variant
        </Button>
        <Button type="button" variant="ghost" size="sm" disabled={isPending} onClick={() => feedbackMutation.mutate('taxonomy_issue')}>
          Mark taxonomy issue
        </Button>
      </div>
    </div>
  );
}
