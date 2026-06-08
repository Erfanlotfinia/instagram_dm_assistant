from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import SuggestedReplyGeneratedBy, SuggestedReplyStatus
from app.domain.models import SuggestedReply, User
from app.schemas.suggested_reply import SuggestedReplyEditAndSend, SuggestedReplyRead, SuggestedReplyReject
from app.services.audit_service import AuditService
from app.services.instagram_send_service import InstagramSendService
from app.services.shop_service import ShopService


class SuggestedReplyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)

    def create_agent_suggestion(
        self,
        *,
        shop_id: UUID,
        conversation_id: UUID,
        message_id: UUID | None,
        text: str,
        reason: str | None,
    ) -> SuggestedReply:
        reply = SuggestedReply(
            shop_id=shop_id,
            conversation_id=conversation_id,
            message_id=message_id,
            suggested_text=text,
            reason=reason,
            generated_by=SuggestedReplyGeneratedBy.AGENT,
        )
        self.db.add(reply)
        AuditService(self.db).log(
            action="suggested_reply_created",
            entity_type="suggested_reply",
            shop_id=shop_id,
            entity_id=str(reply.id),
            metadata={"conversation_id": str(conversation_id), "reason": reason},
        )
        return reply

    def list_for_shop(self, shop_id: UUID, user: User, conversation_id: UUID | None = None) -> list[SuggestedReplyRead]:
        self.shop_service.get_shop(shop_id, user)
        stmt = select(SuggestedReply).where(SuggestedReply.shop_id == shop_id)
        if conversation_id is not None:
            stmt = stmt.where(SuggestedReply.conversation_id == conversation_id)
        stmt = stmt.order_by(SuggestedReply.created_at.desc())
        return [SuggestedReplyRead.model_validate(item) for item in self.db.scalars(stmt).all()]

    def approve_and_send(self, shop_id: UUID, reply_id: UUID, user: User) -> SuggestedReplyRead:
        reply = self._get_pending(shop_id, reply_id, user)
        message = InstagramSendService(self.db).send_text_message(reply.conversation_id, reply.suggested_text, commit=False)
        reply.status = SuggestedReplyStatus.SENT
        reply.approved_by_user_id = user.id
        AuditService(self.db).log(action="reply_approved", entity_type="suggested_reply", shop_id=shop_id, actor_user_id=user.id, entity_id=str(reply.id), metadata={"message_id": str(message.id)})
        self.db.commit()
        self.db.refresh(reply)
        return SuggestedReplyRead.model_validate(reply)

    def edit_and_send(self, shop_id: UUID, reply_id: UUID, payload: SuggestedReplyEditAndSend, user: User) -> SuggestedReplyRead:
        reply = self._get_pending(shop_id, reply_id, user)
        message = InstagramSendService(self.db).send_text_message(reply.conversation_id, payload.edited_text, commit=False)
        reply.status = SuggestedReplyStatus.SENT
        reply.edited_text = payload.edited_text
        reply.approved_by_user_id = user.id
        AuditService(self.db).log(action="reply_edited", entity_type="suggested_reply", shop_id=shop_id, actor_user_id=user.id, entity_id=str(reply.id), metadata={"message_id": str(message.id)})
        self.db.commit()
        self.db.refresh(reply)
        return SuggestedReplyRead.model_validate(reply)

    def reject(self, shop_id: UUID, reply_id: UUID, payload: SuggestedReplyReject, user: User) -> SuggestedReplyRead:
        reply = self._get_pending(shop_id, reply_id, user)
        reply.status = SuggestedReplyStatus.REJECTED
        reply.reason = payload.reason or reply.reason
        AuditService(self.db).log(action="reply_rejected", entity_type="suggested_reply", shop_id=shop_id, actor_user_id=user.id, entity_id=str(reply.id), metadata={"reason": payload.reason})
        self.db.commit()
        self.db.refresh(reply)
        return SuggestedReplyRead.model_validate(reply)

    def _get_pending(self, shop_id: UUID, reply_id: UUID, user: User) -> SuggestedReply:
        self.shop_service.get_shop(shop_id, user)
        reply = self.db.get(SuggestedReply, reply_id)
        if reply is None or reply.shop_id != shop_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggested reply not found")
        if reply.status != SuggestedReplyStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Suggested reply is not pending")
        return reply
