from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from fastapi import HTTPException, status

from app.domain.enums import InventoryReservationStatus, PaymentRecordStatus

StateT = TypeVar("StateT")


@dataclass(frozen=True)
class StateTransition(Generic[StateT]):
    from_state: StateT
    to_state: StateT
    reason: str = "service_transition"


class StrictStateMachine(Generic[StateT]):
    """Small reusable state-machine that rejects undefined transitions."""

    def __init__(self, allowed: set[tuple[StateT, StateT]], *, name: str) -> None:
        self.allowed = allowed
        self.name = name

    def assert_transition(self, from_state: StateT, to_state: StateT) -> None:
        if from_state == to_state:
            return
        if (from_state, to_state) not in self.allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {self.name} transition: {from_state.value} -> {to_state.value}",
            )

    def transition(self, entity: object, to_state: StateT, *, attr: str = "status") -> StateTransition[StateT]:
        from_state = getattr(entity, attr)
        self.assert_transition(from_state, to_state)
        setattr(entity, attr, to_state)
        return StateTransition(from_state, to_state)


PAYMENT_STATE_MACHINE = StrictStateMachine[PaymentRecordStatus](
    {
        (PaymentRecordStatus.CREATED, PaymentRecordStatus.PENDING),
        (PaymentRecordStatus.CREATED, PaymentRecordStatus.PAID),
        (PaymentRecordStatus.CREATED, PaymentRecordStatus.FAILED),
        (PaymentRecordStatus.PENDING, PaymentRecordStatus.PAID),
        (PaymentRecordStatus.PENDING, PaymentRecordStatus.FAILED),
        (PaymentRecordStatus.PENDING, PaymentRecordStatus.CANCELLED),
    },
    name="payment",
)

INVENTORY_RESERVATION_STATE_MACHINE = StrictStateMachine[InventoryReservationStatus](
    {
        (InventoryReservationStatus.ACTIVE, InventoryReservationStatus.RELEASED),
        (InventoryReservationStatus.ACTIVE, InventoryReservationStatus.CONFIRMED),
        (InventoryReservationStatus.ACTIVE, InventoryReservationStatus.EXPIRED),
        (InventoryReservationStatus.CONFIRMED, InventoryReservationStatus.RELEASED),
        (InventoryReservationStatus.RELEASED, InventoryReservationStatus.EXPIRED),
    },
    name="inventory reservation",
)
