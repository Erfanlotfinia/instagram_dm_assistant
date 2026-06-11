from decimal import Decimal
from uuid import UUID

from app.domain.enums import OrderStatus
from app.domain.models import ConversationSlots, Order, Product, ProductVariant
from app.tests.fixtures.agent import build_orchestrator, create_text_message, seed_order_flow_data

__all__ = [
    "build_orchestrator",
    "create_text_message",
    "seed_complete_slots",
    "seed_draft_order",
    "seed_order_flow_data",
]


def seed_complete_slots(db_session, conversation_id: UUID) -> ConversationSlots:
    from app.repositories.conversation_slots_repository import ConversationSlotsRepository

    slots = ConversationSlotsRepository(db_session).get_or_create(conversation_id)
    slots.product_id = None
    slots.product_variant_id = None
    slots.color = "Black"
    slots.size = "L"
    slots.quantity = 1
    slots.customer_name = "Ali Rezaei"
    slots.phone = "09121234567"
    slots.city = "Tehran"
    slots.address = "Valiasr St 10"
    slots.postal_code = "1234567890"
    slots.missing_fields = []
    slots.confidence = {}
    db_session.commit()
    db_session.refresh(slots)
    return slots


def seed_draft_order(
    db_session,
    *,
    shop_id,
    customer_id,
    conversation_id,
    product: Product,
    variant: ProductVariant,
) -> Order:
    order = Order(
        shop_id=shop_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        status=OrderStatus.READY_FOR_CONFIRMATION,
        subtotal_amount=Decimal("49.99"),
        total_amount=Decimal("49.99"),
        currency="USD",
        customer_name="Ali Rezaei",
        phone="09121234567",
        city="Tehran",
        address="Valiasr St 10",
        postal_code="1234567890",
    )
    db_session.add(order)
    db_session.flush()
    from app.domain.models import OrderItem

    db_session.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_variant_id=variant.id,
            product_title_snapshot=product.title,
            variant_color_snapshot=variant.color,
            variant_size_snapshot=variant.size,
            sku_snapshot=variant.sku,
            quantity=1,
            unit_price=Decimal("49.99"),
            total_price=Decimal("49.99"),
        )
    )
    db_session.commit()
    db_session.refresh(order)
    return order
