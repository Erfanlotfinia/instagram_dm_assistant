from decimal import Decimal
from uuid import UUID

from app.domain.enums import AgentWorkflowState, OrderStatus
from app.domain.models import Conversation, ConversationSlots, Message, Order, Product, ProductVariant
from app.tests.fixtures.agent import build_orchestrator, seed_order_flow_data


def seed_complete_slots(db_session, conversation_id: UUID) -> ConversationSlots:
    slots = ConversationSlots(
        conversation_id=conversation_id,
        product_id=None,
        product_variant_id=None,
        color="Black",
        size="L",
        quantity=1,
        customer_name="Ali Rezaei",
        phone="09121234567",
        city="Tehran",
        address="Valiasr St 10",
        postal_code="1234567890",
        missing_fields=[],
        confidence={},
    )
    db_session.add(slots)
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


def create_text_message(db_session, conversation_id: UUID, text: str) -> Message:
    from app.domain.enums import MessageChannel, MessageDirection, MessageType

    message = Message(
        conversation_id=conversation_id,
        direction=MessageDirection.INBOUND,
        channel=MessageChannel.INSTAGRAM,
        message_type=MessageType.TEXT,
        text=text,
        raw_payload={},
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    return message
