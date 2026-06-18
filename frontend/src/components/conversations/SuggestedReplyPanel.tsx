import type { SuggestedReply } from '../../types/conversation';
import { Badge, Button, Field } from '../ui';
import { cn } from '../../lib/cn';

interface SuggestedReplyPanelProps {
  reply: SuggestedReply | undefined;
  editedText: string;
  previewReason?: string | null;
  onEdit: (text: string) => void;
  onApprove: () => void;
  onEditAndSend: () => void;
  onReject: () => void;
  isApproving?: boolean;
  isEditing?: boolean;
  isRejecting?: boolean;
}

export function SuggestedReplyPanel({
  reply,
  editedText,
  previewReason,
  onEdit,
  onApprove,
  onEditAndSend,
  onReject,
  isApproving,
  isEditing,
  isRejecting,
}: SuggestedReplyPanelProps) {
  if (!reply) {
    return null;
  }

  const reason = reply.reason ?? previewReason ?? 'Preview required';

  return (
    <section
      className="rounded-lg border border-warning/30 bg-warning-soft/40 p-4"
      aria-label="Suggested reply card"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-warning">Agent suggestion</p>
          <p className="mt-0.5 text-sm text-fg">{reason}</p>
        </div>
        <Badge tone="warning" dot>
          Needs review
        </Badge>
      </div>

      <blockquote className="mt-3 rounded-md border border-border bg-surface px-3 py-2 text-sm text-fg" dir="auto">
        {reply.suggested_text}
      </blockquote>

      <Field label="Edit before sending" className="mt-3">
        <textarea
          rows={3}
          value={editedText}
          onChange={(event) => onEdit(event.target.value)}
          dir="auto"
          className={cn(
            'w-full resize-y rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg',
            'placeholder:text-subtle focus:border-accent focus:outline-none',
          )}
        />
      </Field>

      <div className="mt-3 flex flex-wrap gap-2">
        <Button type="button" onClick={onApprove} disabled={isApproving}>
          {isApproving ? 'Sending…' : 'Approve and send'}
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={onEditAndSend}
          disabled={!editedText.trim() || isEditing}
        >
          {isEditing ? 'Sending…' : 'Edit and send'}
        </Button>
        <Button type="button" variant="danger" onClick={onReject} disabled={isRejecting}>
          Reject
        </Button>
      </div>
    </section>
  );
}
