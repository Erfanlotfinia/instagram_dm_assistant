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
    return <p className="empty-state">No pending suggested reply.</p>;
  }

  return (
    <div className="suggested-reply-card" aria-label="Suggested reply card">
      <p>
        <strong>Reason:</strong> {reply.reason ?? previewReason ?? 'Preview required'}
      </p>
      <p>{reply.suggested_text}</p>
      <label className="form-field">
        <span>Edit before sending</span>
        <textarea rows={4} value={editedText} onChange={(event) => onEdit(event.target.value)} />
      </label>
      <div className="button-row">
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
          disabled={!editedText || isEditing}
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
    </div>
  );
}
