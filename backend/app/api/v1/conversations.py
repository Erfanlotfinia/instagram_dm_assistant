from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, rate_limit_outbound_message, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import ConversationPriorityLevel, ConversationState, UserRole
from app.domain.models import ShopMember, User
from app.schemas.conversation import (
    ConversationAssignRequest,
    ConversationAssignResponse,
    ConversationDetailRead,
    ConversationHandoffResponse,
    ConversationListFilters,
    ConversationRead,
    ConversationResolveResponse,
    ConversationResponseModeRequest,
    CustomerRead,
    MessageCreate,
    MessageRead,
)
from app.schemas.customer import CustomerUpdate
from app.schemas.order import OrderRead
from app.realtime import publish_event
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
    unassigned: bool | None = None,
    updated_from: datetime | None = None,
    updated_to: datetime | None = None,
    search: str | None = None,
    priority_level: ConversationPriorityLevel | None = None,
    urgent: bool | None = None,
    high_priority: bool | None = None,
    needs_attention: bool | None = None,
    waiting_for_payment: bool | None = None,
    ready_to_order: bool | None = None,
    low_confidence: bool | None = None,
    is_simulation: bool | None = None,
    assigned_to_me: bool | None = None,
) -> list[ConversationRead]:
    priority_levels: list[ConversationPriorityLevel] | None = None
    if urgent:
        priority_level = ConversationPriorityLevel.URGENT
    elif high_priority:
        priority_levels = [ConversationPriorityLevel.URGENT, ConversationPriorityLevel.HIGH]

    operator_id = assigned_operator_id
    if assigned_to_me:
        operator_id = current_user.id

    filters = ConversationListFilters(
        state=state,
        handoff_required=handoff_required,
        assigned_operator_id=operator_id,
        unassigned=unassigned,
        updated_from=updated_from,
        updated_to=updated_to,
        search=search,
        priority_level=priority_level,
        priority_levels=priority_levels,
        needs_attention=needs_attention,
        waiting_for_payment=waiting_for_payment,
        ready_to_order=ready_to_order,
        low_confidence=low_confidence,
        is_simulation=is_simulation,
    )
    return ConversationService(db).list_conversations(shop_id, current_user, filters)


@router.get("/{conversation_id}", response_model=ConversationDetailRead)
async def get_conversation(
    shop_id: UUID,
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> ConversationDetailRead:
    service = ConversationService(db)
    detail = service.get_conversation_detail(shop_id, conversation_id, current_user)
    try:
        await service.mark_telegram_business_read(shop_id, conversation_id)
    except Exception:
        pass
    return detail


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
    message = ConversationService(db).send_manual_message(shop_id, conversation_id, current_user, payload)
    publish_event(shop_id, "message.created", {"conversation_id": str(conversation_id)})
    return message


@router.post("/{conversation_id}/send-manual-message", response_model=MessageRead, status_code=201)
def send_manual_message(
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
    result = ConversationService(db).take_over(shop_id, conversation_id, current_user)
    publish_event(shop_id, "conversation.updated", {"conversation_id": str(conversation_id)})
    return result


@router.post("/{conversation_id}/response-mode", response_model=ConversationHandoffResponse)
def set_conversation_response_mode(
    shop_id: UUID,
    conversation_id: UUID,
    payload: ConversationResponseModeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ConversationHandoffResponse:
    result = ConversationService(db).set_response_mode(
        shop_id, conversation_id, payload.response_mode, current_user
    )
    publish_event(shop_id, "conversation.updated", {"conversation_id": str(conversation_id)})
    return result


@router.post("/{conversation_id}/release-to-agent", response_model=ConversationHandoffResponse)
def release_conversation_to_agent(
    shop_id: UUID,
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ConversationHandoffResponse:
    return ConversationService(db).release_to_agent(shop_id, conversation_id, current_user)


@router.post("/{conversation_id}/release-agent", response_model=ConversationHandoffResponse)
def release_agent(
    shop_id: UUID,
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ConversationHandoffResponse:
    return ConversationService(db).release_to_agent(shop_id, conversation_id, current_user)


@router.post("/{conversation_id}/assign", response_model=ConversationAssignResponse)
def assign_conversation(
    shop_id: UUID,
    conversation_id: UUID,
    payload: ConversationAssignRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ConversationAssignResponse:
    return ConversationService(db).assign_conversation(
        shop_id, conversation_id, payload.operator_id, current_user
    )


@router.post("/{conversation_id}/mark-resolved", response_model=ConversationResolveResponse)
def mark_conversation_resolved(
    shop_id: UUID,
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> ConversationResolveResponse:
    result = ConversationService(db).mark_resolved(shop_id, conversation_id, current_user)
    publish_event(shop_id, "conversation.updated", {"conversation_id": str(conversation_id)})
    return result


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
