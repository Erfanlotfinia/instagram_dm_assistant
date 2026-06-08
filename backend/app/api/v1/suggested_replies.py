from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, rate_limit_outbound_message, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import ShopMember, User
from app.schemas.suggested_reply import SuggestedReplyEditAndSend, SuggestedReplyRead, SuggestedReplyReject
from app.services.suggested_reply_service import SuggestedReplyService

router = APIRouter(prefix="/shops/{shop_id}/suggested-replies", tags=["suggested-replies"])


@router.get("", response_model=list[SuggestedReplyRead])
def list_suggested_replies(shop_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(get_shop_membership)], db: Annotated[Session, Depends(get_db_session)], conversation_id: UUID | None = None) -> list[SuggestedReplyRead]:
    return SuggestedReplyService(db).list_for_shop(shop_id, current_user, conversation_id)


@router.post("/{reply_id}/approve", response_model=SuggestedReplyRead)
def approve_suggested_reply(shop_id: UUID, reply_id: UUID, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))], _rate_limit: Annotated[None, Depends(rate_limit_outbound_message)], db: Annotated[Session, Depends(get_db_session)]) -> SuggestedReplyRead:
    return SuggestedReplyService(db).approve_and_send(shop_id, reply_id, current_user)


@router.post("/{reply_id}/edit-and-send", response_model=SuggestedReplyRead)
def edit_and_send_suggested_reply(shop_id: UUID, reply_id: UUID, payload: SuggestedReplyEditAndSend, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))], _rate_limit: Annotated[None, Depends(rate_limit_outbound_message)], db: Annotated[Session, Depends(get_db_session)]) -> SuggestedReplyRead:
    return SuggestedReplyService(db).edit_and_send(shop_id, reply_id, payload, current_user)


@router.post("/{reply_id}/reject", response_model=SuggestedReplyRead)
def reject_suggested_reply(shop_id: UUID, reply_id: UUID, payload: SuggestedReplyReject, current_user: Annotated[User, Depends(get_current_user)], _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))], db: Annotated[Session, Depends(get_db_session)]) -> SuggestedReplyRead:
    return SuggestedReplyService(db).reject(shop_id, reply_id, payload, current_user)
