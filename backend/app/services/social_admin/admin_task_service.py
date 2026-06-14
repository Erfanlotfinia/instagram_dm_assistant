from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import AdminTask, User
from app.schemas.social_admin import AdminTaskCreate, AdminTaskRead
from app.services.shop_service import ShopService
from app.services.social_admin.admin_task_engine import AdminTaskEngine

FRONTEND_TASK_ALIASES = {
    "suggest_reply": "reply_suggestion",
    "summarize_conversation": "conversation_summary",
    "faq_mining": "faq_mining",
    "draft_post_caption": "post_caption_draft",
    "draft_story_text": "story_text_draft",
    "draft_campaign_message": "campaign_message_draft",
}


class AdminTaskService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)
        self.engine = AdminTaskEngine()

    def list_tasks(self, shop_id: UUID, user: User, limit: int = 50) -> list[AdminTaskRead]:
        self.shop_service.get_shop(shop_id, user)
        tasks = list(
            self.db.scalars(
                select(AdminTask)
                .where(AdminTask.shop_id == shop_id)
                .order_by(AdminTask.created_at.desc())
                .limit(limit)
            ).all()
        )
        return [AdminTaskRead.model_validate(task) for task in tasks]

    def create_task(self, shop_id: UUID, payload: AdminTaskCreate, user: User) -> AdminTaskRead:
        self.shop_service.get_shop(shop_id, user)
        task_type = FRONTEND_TASK_ALIASES.get(payload.task_type, payload.task_type)
        input_json: dict[str, Any] = {"context": payload.context}
        if payload.conversation_id is not None:
            input_json["conversation_id"] = str(payload.conversation_id)

        try:
            draft = self.engine.generate_draft(task_type, input_json)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        task = AdminTask(
            shop_id=shop_id,
            requested_by_user_id=user.id,
            task_type=task_type,
            input_json=input_json,
            output_json=draft,
            status="completed",
            requires_approval=True,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return AdminTaskRead.model_validate(task)

    def approve_task(self, shop_id: UUID, task_id: UUID, user: User) -> AdminTaskRead:
        task = self._get_task(shop_id, task_id, user)
        if task.status == "approved":
            return AdminTaskRead.model_validate(task)
        task.status = "approved"
        task.approved_by_user_id = user.id
        self.db.commit()
        self.db.refresh(task)
        return AdminTaskRead.model_validate(task)

    def reject_task(self, shop_id: UUID, task_id: UUID, user: User) -> AdminTaskRead:
        task = self._get_task(shop_id, task_id, user)
        task.status = "rejected"
        self.db.commit()
        self.db.refresh(task)
        return AdminTaskRead.model_validate(task)

    def _get_task(self, shop_id: UUID, task_id: UUID, user: User) -> AdminTask:
        self.shop_service.get_shop(shop_id, user)
        task = self.db.scalar(
            select(AdminTask).where(AdminTask.shop_id == shop_id, AdminTask.id == task_id)
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin task not found")
        return task
