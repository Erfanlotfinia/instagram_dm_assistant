from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import OrderPaymentStatus, OrderShippingStatus, OrderStatus, UserRole
from app.domain.models import ShopMember, User
from app.schemas.order import OrderCancelRequest, OrderRead, OrderShipRequest
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.shipping_service import ShippingService

router = APIRouter(prefix="/shops", tags=["orders"])


@router.get("/{shop_id}/orders", response_model=list[OrderRead])
def list_orders(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    status_filter: Annotated[OrderStatus | None, Query(alias="status")] = None,
    payment_status: OrderPaymentStatus | None = None,
    shipping_status: OrderShippingStatus | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> list[OrderRead]:
    from app.schemas.order import OrderListFilters

    filters = OrderListFilters(
        status=status_filter,
        payment_status=payment_status,
        shipping_status=shipping_status,
        created_from=created_from,
        created_to=created_to,
    )
    return OrderService(db).list_orders(shop_id, current_user, filters)


@router.get("/{shop_id}/orders/{order_id}", response_model=OrderRead)
def get_order(
    shop_id: UUID,
    order_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderRead:
    return OrderService(db).get_order_read(shop_id, order_id, current_user)


@router.post("/{shop_id}/orders/{order_id}/confirm", response_model=OrderRead)
def confirm_order(
    shop_id: UUID,
    order_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderRead:
    return OrderService(db).confirm_order(shop_id, order_id, current_user)


@router.post("/{shop_id}/orders/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    shop_id: UUID,
    order_id: UUID,
    payload: OrderCancelRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderRead:
    return OrderService(db).cancel_order(shop_id, order_id, current_user, payload)


@router.post("/{shop_id}/orders/{order_id}/mark-paid", response_model=OrderRead)
def mark_order_paid(
    shop_id: UUID,
    order_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderRead:
    order = PaymentService(db).mark_paid_manually(shop_id, order_id, current_user)
    return OrderService(db).get_order_read(shop_id, order.id, current_user)


@router.post("/{shop_id}/orders/{order_id}/ship", response_model=OrderRead)
def ship_order(
    shop_id: UUID,
    order_id: UUID,
    payload: OrderShipRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    _: Annotated[ShopMember, Depends(require_shop_role(UserRole.OPERATOR))],
    db: Annotated[Session, Depends(get_db_session)],
) -> OrderRead:
    order = ShippingService(db).ship_order(shop_id, order_id, payload, current_user)
    return OrderService(db).get_order_read(shop_id, order.id, current_user)
