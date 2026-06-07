from decimal import Decimal
from uuid import uuid4

from app.domain.enums import AgentIntent, AgentWorkflowState
from app.domain.models import ConversationSlots, ProductVariant
from app.services.state_machine_service import (
    check_inventory,
    decide_next_state,
    match_variant,
)


def _variant(color: str, size: str, stock: int = 5) -> ProductVariant:
    return ProductVariant(
        id=uuid4(),
        product_id=uuid4(),
        color=color,
        size=size,
        sku=f"{color}-{size}",
        price=Decimal("100.00"),
        stock_quantity=stock,
        reserved_quantity=0,
        is_active=True,
    )


def test_match_variant_finds_black_size_l() -> None:
    variants = [_variant("Black", "L"), _variant("White", "M")]
    result = match_variant(variants, "black", "L")
    assert result.variant is not None
    assert result.variant.color == "Black"
    assert result.invalid_color is False
    assert result.invalid_size is False


def test_match_variant_detects_invalid_color() -> None:
    variants = [_variant("Black", "L")]
    result = match_variant(variants, "blue", "L")
    assert result.variant is None
    assert result.invalid_color is True


def test_decide_next_state_waiting_for_customer_info() -> None:
    slots = ConversationSlots(
        conversation_id=uuid4(),
        product_id=uuid4(),
        product_variant_id=uuid4(),
        color="Black",
        size="L",
        quantity=1,
        missing_fields=[],
        confidence={},
    )
    decision = decide_next_state(
        AgentWorkflowState.WAITING_FOR_VARIANT,
        AgentIntent.BUY_PRODUCT,
        slots,
        product_resolved=True,
        variant_resolved=True,
        inventory_available=True,
        needs_human=False,
    )
    assert decision.next_state == AgentWorkflowState.WAITING_FOR_CUSTOMER_INFO
    assert "customer_name" in decision.missing_fields


def test_check_inventory_respects_available_stock() -> None:
    variant = _variant("Black", "L", stock=2)
    assert check_inventory(variant, 2) is True
    assert check_inventory(variant, 3) is False
