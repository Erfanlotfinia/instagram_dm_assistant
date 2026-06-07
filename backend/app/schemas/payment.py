from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import PaymentRecordStatus


class MockPaymentCallbackRequest(BaseModel):
    payment_id: UUID
    status: PaymentRecordStatus = PaymentRecordStatus.PAID
    provider_reference: str | None = Field(default=None, max_length=255)
