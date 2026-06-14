from __future__ import annotations

from typing import Any

TASK_LABELS = {
    "reply_suggestion": "Suggest reply",
    "conversation_summary": "Summarize conversation",
    "faq_mining": "FAQ mining",
    "post_caption_draft": "Draft post caption",
    "story_text_draft": "Draft story text",
    "campaign_message_draft": "Draft campaign message",
    "product_announcement": "Product announcement",
    "recovery_message": "Recovery message",
    "comparison_response": "Comparison response",
}


class AdminTaskEngine:
    allowed = {
        "reply_suggestion",
        "conversation_summary",
        "faq_mining",
        "post_caption_draft",
        "story_text_draft",
        "campaign_message_draft",
        "product_announcement",
        "recovery_message",
        "comparison_response",
    }

    def generate_draft(self, task_type: str, input_json: dict[str, Any]) -> dict[str, Any]:
        if task_type not in self.allowed:
            raise ValueError("unsupported admin task")
        context = (
            input_json.get("context")
            or input_json.get("topic")
            or input_json.get("product")
            or "selected catalog context"
        )
        label = TASK_LABELS.get(task_type, task_type.replace("_", " "))
        draft_body = (
            f"{label} draft\n\n"
            f"Context: {context}\n\n"
            f"This draft is grounded in shop context and held for operator approval. "
            f"Nothing will be published automatically."
        )
        return {
            "draft": draft_body,
            "auto_publish": False,
            "schema_version": "admin-task-v1",
            "task_type": task_type,
        }
