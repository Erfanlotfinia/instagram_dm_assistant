import { useState } from 'react';

import { Button } from '../ui';
import type { InstagramCandidateAccount } from '../../types/channel';

interface InstagramAccountSelectionProps {
  candidates: InstagramCandidateAccount[];
  disabled?: boolean;
  onSelect: (candidate: InstagramCandidateAccount) => Promise<void>;
}

export function InstagramAccountSelection({
  candidates,
  disabled = false,
  onSelect,
}: InstagramAccountSelectionProps) {
  const [selectedId, setSelectedId] = useState<string | null>(
    candidates[0]?.instagram_business_account_id ?? null,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const selected = candidates.find(
    (item) => item.instagram_business_account_id === selectedId,
  );

  async function handleSubmit() {
    if (!selected) {
      return;
    }
    setIsSubmitting(true);
    try {
      await onSelect(selected);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted">
        Multiple Instagram Business accounts were found. Select the account you want Modira to use.
      </p>
      <div className="flex flex-col gap-2">
        {candidates.map((candidate) => (
          <label
            key={candidate.instagram_business_account_id}
            className="flex cursor-pointer items-start gap-3 rounded-lg border border-border px-4 py-3"
          >
            <input
              type="radio"
              name="instagram-account"
              checked={selectedId === candidate.instagram_business_account_id}
              onChange={() => setSelectedId(candidate.instagram_business_account_id)}
              disabled={disabled || isSubmitting}
              className="mt-1"
            />
            <span>
              <span className="block text-sm font-medium text-fg">
                {candidate.instagram_username
                  ? `@${candidate.instagram_username}`
                  : candidate.page_name}
              </span>
              <span className="block text-xs text-muted">
                Page: {candidate.page_name} · ID {candidate.instagram_business_account_id}
              </span>
            </span>
          </label>
        ))}
      </div>
      <Button type="button" onClick={() => void handleSubmit()} disabled={disabled || !selected || isSubmitting}>
        {isSubmitting ? 'Connecting…' : 'Connect selected account'}
      </Button>
    </div>
  );
}
