from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.schemas.order import OrderRead
from app.schemas.payment import MockPaymentCallbackRequest
from app.services.channel_outbound_service import ChannelOutboundService, payment_paid_key
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/mock/callback", response_model=OrderRead)
def mock_payment_callback(
    payload: MockPaymentCallbackRequest,
    db: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> OrderRead:
    payment_service = PaymentService(db, settings=settings)
    order = payment_service.handle_mock_callback(
        payload.payment_id,
        payload.status,
        provider_reference=payload.provider_reference,
        raw_payload=payload.model_dump(mode="json"),
    )

    if payload.status.value == "paid":
        send_service = ChannelOutboundService(db, settings)
        message = (
            f"پرداخت شما با موفقیت انجام شد.\n"
            f"شماره سفارش: {order.id}\n"
            f"مبلغ: {order.total_amount} {order.currency}\n"
            "به زودی سفارش شما ارسال می‌شود."
        )
        send_service.send_text_message(
            order.conversation_id,
            message,
            idempotency_key=payment_paid_key(payload.payment_id),
        )

    return OrderService(db, settings=settings)._to_read(order)


@router.get("/mock/pay/{payment_id}", status_code=status.HTTP_200_OK)
def mock_payment_page(
    payment_id: UUID,
    db: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    """Dev-friendly mock pay endpoint; triggers paid callback."""
    payment_service = PaymentService(db, settings=settings)
    from app.domain.enums import PaymentRecordStatus

    order = payment_service.handle_mock_callback(payment_id, PaymentRecordStatus.PAID)
    send_service = ChannelOutboundService(db, settings)
    message = (
        f"پرداخت شما با موفقیت انجام شد.\n"
        f"شماره سفارش: {order.id}\n"
        f"مبلغ: {order.total_amount} {order.currency}\n"
        "به زودی سفارش شما ارسال می‌شود."
    )
    send_service.send_text_message(
        order.conversation_id,
        message,
        idempotency_key=payment_paid_key(payment_id),
    )
    return {"status": "paid", "order_id": str(order.id)}
