"""Property-style tests for invalid order state machine transitions."""

import pytest

from app.domain.enums import OrderCorrectnessAction, OrderStatus
from app.services.order_state_machine_service import OrderStateMachineService


@pytest.fixture
def sm() -> OrderStateMachineService:
    return OrderStateMachineService.__new__(OrderStateMachineService)


@pytest.mark.parametrize(
    ("from_status", "action"),
    [
        (s, a)
        for s in OrderStatus
        for a in OrderCorrectnessAction
        if OrderStateMachineService.__new__(OrderStateMachineService).can_transition(s, a) is None
    ],
)
def test_invalid_transition_returns_none(sm: OrderStateMachineService, from_status: OrderStatus, action: OrderCorrectnessAction) -> None:
    assert sm.can_transition(from_status, action) is None


def test_cancelled_has_no_outgoing_transitions(sm: OrderStateMachineService) -> None:
    for action in OrderCorrectnessAction:
        assert sm.can_transition(OrderStatus.CANCELLED, action) is None


def test_order_created_is_terminal(sm: OrderStateMachineService) -> None:
    for action in OrderCorrectnessAction:
        result = sm.can_transition(OrderStatus.ORDER_CREATED, action)
        assert result is None or result == OrderStatus.ORDER_CREATED
