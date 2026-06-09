from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import PaymentProvider, PaymentRecordStatus
from app.domain.models import Order, Payment
from app.repositories.payment_repository import PaymentRepository


class PaymentProviderBase(ABC):
    @abstractmethod
    def create_payment(self, order: Order) -> Payment:
        raise NotImplementedError


class MockPaymentProvider(PaymentProviderBase):
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.payments = PaymentRepository(db)

    def create_payment(self, order: Order) -> Payment:
        payment = Payment(
            order_id=order.id,
            provider=PaymentProvider.MOCK,
            status=PaymentRecordStatus.PENDING,
        )
        self.payments.create(payment)
        base_url = self.settings.api_public_base_url.rstrip("/")
        payment.payment_url = f"{base_url}/api/v1/payments/mock/pay/{payment.id}"
        payment.provider_reference = f"mock-{payment.id}"
        return payment


def get_payment_provider(db: Session, provider: PaymentProvider = PaymentProvider.MOCK) -> PaymentProviderBase:
    if provider == PaymentProvider.MOCK:
        return MockPaymentProvider(db)
    raise ValueError(f"Unsupported payment provider: {provider}")
