from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.enums import AgentIntent, AgentWorkflowState
from app.domain.models import ConversationSlots, ProductVariant
from app.services.slot_merge_service import compute_missing_fields, normalize_variant_value


@dataclass
class VariantMatchResult:
    variant: ProductVariant | None
    invalid_color: bool = False
    invalid_size: bool = False


@dataclass
class StateDecision:
    next_state: AgentWorkflowState
    missing_fields: list[str]
    variant_match: VariantMatchResult | None = None


def match_variant(
    variants: list[ProductVariant],
    color: str | None,
    size: str | None,
) -> VariantMatchResult:
    normalized_color = normalize_variant_value(color)
    normalized_size = normalize_variant_value(size)

    if not normalized_color and not normalized_size:
        return VariantMatchResult(variant=None)

    available_colors = {
        normalize_variant_value(variant.color)
        for variant in variants
        if variant.is_active and variant.color
    }
    available_sizes = {
        normalize_variant_value(variant.size)
        for variant in variants
        if variant.is_active and variant.size
    }

    invalid_color = bool(normalized_color and normalized_color not in available_colors)
    invalid_size = bool(normalized_size and normalized_size not in available_sizes)

    for variant in variants:
        if not variant.is_active:
            continue
        variant_color = normalize_variant_value(variant.color)
        variant_size = normalize_variant_value(variant.size)
        color_ok = normalized_color is None or variant_color == normalized_color
        size_ok = normalized_size is None or variant_size == normalized_size
        if color_ok and size_ok and (normalized_color or normalized_size):
            return VariantMatchResult(variant=variant, invalid_color=invalid_color, invalid_size=invalid_size)

    return VariantMatchResult(variant=None, invalid_color=invalid_color, invalid_size=invalid_size)


def decide_next_state(
    current_state: AgentWorkflowState,
    intent: AgentIntent,
    slots: ConversationSlots,
    *,
    product_resolved: bool,
    variant_resolved: bool,
    inventory_available: bool | None,
    needs_human: bool,
) -> StateDecision:
    if needs_human or intent == AgentIntent.HUMAN_HELP:
        return StateDecision(
            next_state=AgentWorkflowState.HUMAN_HANDOFF,
            missing_fields=slots.missing_fields,
        )

    if intent == AgentIntent.CANCEL_ORDER:
        return StateDecision(next_state=AgentWorkflowState.CANCELLED, missing_fields=[])

    if intent == AgentIntent.CONFIRM_ORDER and current_state == AgentWorkflowState.WAITING_FOR_CONFIRMATION:
        if inventory_available is False:
            return StateDecision(
                next_state=AgentWorkflowState.WAITING_FOR_VARIANT,
                missing_fields=["stock"],
            )
        return StateDecision(next_state=AgentWorkflowState.WAITING_FOR_PAYMENT, missing_fields=[])

    if not product_resolved or slots.product_id is None:
        return StateDecision(
            next_state=AgentWorkflowState.WAITING_FOR_PRODUCT,
            missing_fields=["product"],
        )

    if not variant_resolved or slots.product_variant_id is None:
        missing = compute_missing_fields(slots, require_variant=True)
        return StateDecision(
            next_state=AgentWorkflowState.WAITING_FOR_VARIANT,
            missing_fields=missing,
        )

    if inventory_available is False:
        return StateDecision(
            next_state=AgentWorkflowState.WAITING_FOR_VARIANT,
            missing_fields=["stock"],
        )

    customer_missing = compute_missing_fields(slots, require_variant=False)
    customer_missing = [field for field in customer_missing if field not in ("product", "color", "size", "quantity")]
    if customer_missing:
        return StateDecision(
            next_state=AgentWorkflowState.WAITING_FOR_CUSTOMER_INFO,
            missing_fields=customer_missing,
        )

    if intent == AgentIntent.CONFIRM_ORDER or current_state == AgentWorkflowState.WAITING_FOR_CONFIRMATION:
        return StateDecision(next_state=AgentWorkflowState.WAITING_FOR_CONFIRMATION, missing_fields=[])

    if current_state in {
        AgentWorkflowState.WAITING_FOR_PAYMENT,
        AgentWorkflowState.PAID,
        AgentWorkflowState.SENT_TO_SHIPPING,
        AgentWorkflowState.COMPLETED,
    }:
        return StateDecision(next_state=current_state, missing_fields=[])

    if current_state == AgentWorkflowState.CANCELLED:
        return StateDecision(next_state=AgentWorkflowState.CANCELLED, missing_fields=[])

    if current_state == AgentWorkflowState.HUMAN_HANDOFF:
        return StateDecision(next_state=AgentWorkflowState.HUMAN_HANDOFF, missing_fields=slots.missing_fields)

    return StateDecision(next_state=AgentWorkflowState.WAITING_FOR_CONFIRMATION, missing_fields=[])


def available_stock(variant: ProductVariant) -> int:
    return variant.stock_quantity - variant.reserved_quantity


def check_inventory(variant: ProductVariant, quantity: int | None) -> bool:
    requested = quantity or 1
    return available_stock(variant) >= requested
