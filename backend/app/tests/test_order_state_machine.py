"""Unit tests for order state machine valid transitions."""

from app.domain.enums import OrderCorrectnessAction, OrderStatus
from app.services.order_state_machine_service import OrderStateMachineService


def test_all_valid_transitions_defined() -> None:
    sm = OrderStateMachineService.__new__(OrderStateMachineService)
    pairs = sm.all_valid_pairs()
    assert len(pairs) >= 10
    for from_status, action, to_status in pairs:
        assert sm.can_transition(from_status, action) == to_status


def test_draft_to_ready_via_confirm() -> None:
    sm = OrderStateMachineService.__new__(OrderStateMachineService)
    assert sm.can_transition(OrderStatus.DRAFT, OrderCorrectnessAction.CONFIRM) == OrderStatus.READY_FOR_CONFIRMATION


def test_ready_to_reserved_via_reserve() -> None:
    sm = OrderStateMachineService.__new__(OrderStateMachineService)
    assert sm.can_transition(OrderStatus.READY_FOR_CONFIRMATION, OrderCorrectnessAction.RESERVE) == OrderStatus.RESERVED


def test_payment_pending_to_paid() -> None:
    sm = OrderStateMachineService.__new__(OrderStateMachineService)
    assert sm.can_transition(OrderStatus.PAYMENT_PENDING, OrderCorrectnessAction.MARK_PAID) == OrderStatus.PAID


def test_paid_to_order_created() -> None:
    sm = OrderStateMachineService.__new__(OrderStateMachineService)
    assert sm.can_transition(OrderStatus.PAID, OrderCorrectnessAction.COMPLETE) == OrderStatus.ORDER_CREATED
