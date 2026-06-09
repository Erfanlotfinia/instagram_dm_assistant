from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_minimum_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import User
from app.schemas.order_correctness import (
    OrderCancelRequest,
    OrderClarifyRequest,
    OrderConfirmRequest,
    OrderCorrectnessRead,
    OrderDraftCreateRequest,
    OrderReserveRequest,
    OrderTimelineResponse,
)
from app.services.order_correctness_service import OrderCorrectnessService

router = APIRouter(prefix="/orders", tags=["order-correctness"])


@router.post("/draft", response_model=OrderCorrectnessRead)
def create_draft(
    payload: OrderDraftCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderCorrectnessRead:
    return OrderCorrectnessService(db).create_draft(payload, current_user)


@router.post("/{order_id}/clarify", response_model=OrderCorrectnessRead)
def clarify_order(
    order_id: UUID,
    payload: OrderClarifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[User, Depends(require_minimum_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderCorrectnessRead:
    return OrderCorrectnessService(db).clarify(order_id, current_user, payload)


@router.post("/{order_id}/confirm", response_model=OrderCorrectnessRead)
def confirm_order(
    order_id: UUID,
    payload: OrderConfirmRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[User, Depends(require_minimum_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderCorrectnessRead:
    return OrderCorrectnessService(db).confirm(order_id, current_user, payload)


@router.post("/{order_id}/reserve", response_model=OrderCorrectnessRead)
def reserve_order(
    order_id: UUID,
    payload: OrderReserveRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[User, Depends(require_minimum_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderCorrectnessRead:
    return OrderCorrectnessService(db).reserve(order_id, current_user, payload)


@router.post("/{order_id}/payment-link", response_model=OrderCorrectnessRead)
def payment_link_order(
    order_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[User, Depends(require_minimum_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderCorrectnessRead:
    return OrderCorrectnessService(db).payment_link(order_id, current_user)


@router.post("/{order_id}/complete", response_model=OrderCorrectnessRead)
def complete_order(
    order_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[User, Depends(require_minimum_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderCorrectnessRead:
    return OrderCorrectnessService(db).complete(order_id, current_user)


@router.post("/{order_id}/cancel", response_model=OrderCorrectnessRead)
def cancel_order(
    order_id: UUID,
    payload: OrderCancelRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[User, Depends(require_minimum_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderCorrectnessRead:
    return OrderCorrectnessService(db).cancel(order_id, current_user, payload)


@router.get("/{order_id}", response_model=OrderCorrectnessRead)
def get_order(
    order_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderCorrectnessRead:
    return OrderCorrectnessService(db).get_order(order_id, current_user)


@router.get("/{order_id}/timeline", response_model=OrderTimelineResponse)
def get_order_timeline(
    order_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderTimelineResponse:
    return OrderCorrectnessService(db).get_timeline(order_id, current_user)
