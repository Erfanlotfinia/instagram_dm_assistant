from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, rate_limit_outbound_message, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import ConversationState, UserRole
from app.domain.models import ShopMember, User
from app.schemas.conversation import (
    ConversationDetailRead,
    ConversationHandoffResponse,
    ConversationListFilters,
    ConversationRead,
    ConversationResolveResponse,
    CustomerRead,
    CustomerUpdate,
    MessageCreate,
    MessageRead,
)
from app.schemas.order import OrderRead
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/shops/{shop_id}/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationRead])
def list_conversations(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    state: ConversationState | None = None,
    handoff_required: bool | None = None,
    assigned_operator_id: UUID | None = None,
    updated_from: datetime | None = None,
    updated_to: datetime | None = None,
    search: str | None = None,
) -> list[ConversationRead]:
    filters = ConversationListFilters(
        state=state,
        handoff_required=handoff_required,
        assigned_operator_id=assigned_operator_id,
        updated_from=updated_from,
        updated_to=updated_to,
        search=search,
    )
    return ConversationService(db).list_conversations(shop_id, current_user, filters)


@router.get("/{conversation_id}", response_model=ConversationDetailRead)
def get_conversation(
    shop_id: UUID,
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ConversationDetailRead:
    return ConversationService(db).get_conversation_detail(shop_id, conversation_id, current_user)


@router.post("/{conversation_id}/messages", response_model=MessageRead, status_code=201)
def send_conversation_message(
    shop_id: UUID,
    conversation_id: UUID,
    payload: MessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    _rate_limit: Annotated[None, Depends(rate_limit_outbound_message)],
    db: Annotated[Session, Depends(get_db_session)],
) -> MessageRead:
    return ConversationService(db).send_manual_message(shop_id, conversation_id, current_user, payload)


@router.post("/{conversation_id}/take-over", response_model=ConversationHandoffResponse)
def take_over_conversation(
    shop_id: UUID,
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ConversationHandoffResponse:
    return ConversationService(db).take_over(shop_id, conversation_id, current_user)


@router.post("/{conversation_id}/release-to-agent", response_model=ConversationHandoffResponse)
def release_conversation_to_agent(
    shop_id: UUID,
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ConversationHandoffResponse:
    return ConversationService(db).release_to_agent(shop_id, conversation_id, current_user)


@router.post("/{conversation_id}/mark-resolved", response_model=ConversationResolveResponse)
def mark_conversation_resolved(
    shop_id: UUID,
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ConversationResolveResponse:
    return ConversationService(db).mark_resolved(shop_id, conversation_id, current_user)


@router.patch("/{conversation_id}/customer", response_model=CustomerRead)
def update_conversation_customer(
    shop_id: UUID,
    conversation_id: UUID,
    payload: CustomerUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> CustomerRead:
    return ConversationService(db).update_customer(shop_id, conversation_id, current_user, payload)


@router.post("/{conversation_id}/orders", response_model=OrderRead, status_code=201)
def create_order_from_conversation(
    shop_id: UUID,
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderRead:
    return ConversationService(db).create_order_from_conversation(shop_id, conversation_id, current_user)
