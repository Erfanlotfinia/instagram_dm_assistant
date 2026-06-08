import type { SuggestedReply } from '../../types/conversation';

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
    <section className="suggested-reply-banner" aria-label="Suggested reply card">
      <div className="suggested-reply-banner__header">
        <div>
          <p className="suggested-reply-banner__eyebrow">Agent suggestion</p>
          <p className="suggested-reply-banner__reason">{reason}</p>
        </div>
        <span className="status-pill status-pill--accent">Needs review</span>
      </div>

      <blockquote className="suggested-reply-banner__quote" dir="auto">
        {reply.suggested_text}
      </blockquote>

      <label className="form-field suggested-reply-banner__edit">
        <span>Edit before sending</span>
        <textarea rows={3} value={editedText} onChange={(event) => onEdit(event.target.value)} dir="auto" />
      </label>

      <div className="suggested-reply-banner__actions">
        <button
          className="button button--primary"
          type="button"
          onClick={onApprove}
          disabled={isApproving}
        >
          Approve and send
        </button>
        <button
          className="button button--ghost-dark"
          type="button"
          onClick={onEditAndSend}
          disabled={!editedText.trim() || isEditing}
        >
          Edit and send
        </button>
        <button
          className="button button--danger"
          type="button"
          onClick={onReject}
          disabled={isRejecting}
        >
          Reject
        </button>
      </div>
    </section>
  );
}
