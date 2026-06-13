from __future__ import annotations
from dataclasses import dataclass, field
from uuid import uuid4
from datetime import datetime, timezone
from typing import Any

@dataclass
class AdminTask:
    shop_id: str; requested_by_user_id: str | None; task_type: str; input_json: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4())); output_json: dict[str, Any] = field(default_factory=dict); status: str = "pending"; requires_approval: bool = True; approved_by_user_id: str | None = None; created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc)); updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class AdminTaskEngine:
    allowed = {"reply_suggestion","conversation_summary","faq_mining","post_caption_draft","story_text_draft","campaign_message_draft","product_announcement","recovery_message","comparison_response"}
    def create_task(self, shop_id: str, requested_by_user_id: str | None, task_type: str, input_json: dict[str, Any]) -> AdminTask:
        if task_type not in self.allowed: raise ValueError("unsupported admin task")
        task = AdminTask(shop_id, requested_by_user_id, task_type, input_json)
        topic = input_json.get("topic") or input_json.get("product") or "selected catalog context"
        task.output_json = {"draft": f"Draft {task_type.replace('_',' ')} grounded in {topic}.", "auto_publish": False, "schema_version": "admin-task-v1"}
        task.status = "completed"; task.updated_at = datetime.now(timezone.utc)
        return task
    def approve(self, task: AdminTask, user_id: str) -> AdminTask:
        task.status="approved"; task.approved_by_user_id=user_id; task.updated_at=datetime.now(timezone.utc); return task
    def reject(self, task: AdminTask) -> AdminTask:
        task.status="rejected"; task.updated_at=datetime.now(timezone.utc); return task
