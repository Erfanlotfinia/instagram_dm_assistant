"""Rich demo dataset for exercising all frontend features.

Called from app.scripts.seed after core admin/shop/catalog bootstrap.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import (
    AgentMode,
    AgentWorkflowState,
    ConfidenceSource,
    ConversationPriorityLevel,
    ConversationState,
    InstagramAccountStatus,
    MessageChannel,
    MessageDirection,
    MessageType,
    OrderPaymentStatus,
    OrderShippingStatus,
    OrderStatus,
    ProductStatus,
    SellingStyle,
    SuggestedReplyGeneratedBy,
    SuggestedReplyStatus,
    TriggerSourceType,
    UserRole,
)
from app.domain.models import (
    ColorAlias,
    CommentToDmTrigger,
    Conversation,
    ConversationSlots,
    Customer,
    InstagramAccount,
    InstagramProductMap,
    Message,
    Order,
    OrderItem,
    Product,
    ProductVariant,
    Shop,
    ShopAgentSettings,
    ShopMember,
    SizeAlias,
    SuggestedReply,
    TriggerEvent,
    UnavailableDemandLog,
    User,
)
from app.repositories.shop_repository import ShopMemberRepository, ShopRepository

logger = logging.getLogger(__name__)

SECOND_SHOP_SLUG = "fashion-boutique"
SECOND_SHOP_NAME = "Fashion Boutique"
HOODIE_TITLE = "Classic Hoodie"
DRESS_TITLE = "Summer Linen Dress"
POST_URL_HOODIE = "https://www.instagram.com/p/HOODIE99/"
POST_URL_DRESS = "https://www.instagram.com/p/DRESS88/"


def _get_or_create_product(
    db: Session,
    shop_id: UUID,
    *,
    title: str,
    description: str,
    base_price: Decimal,
    variants: list[dict],
) -> Product:
    product = db.scalar(select(Product).where(Product.shop_id == shop_id, Product.title == title))
    if product is None:
        product = Product(
            shop_id=shop_id,
            title=title,
            description=description,
            status=ProductStatus.ACTIVE,
            base_price=base_price,
            currency="USD",
            category="apparel",
        )
        db.add(product)
        db.flush()
        logger.info("Created demo product: %s", title)

    for spec in variants:
        sku = spec["sku"]
        existing = db.scalar(
            select(ProductVariant).where(
                ProductVariant.product_id == product.id,
                ProductVariant.sku == sku,
            )
        )
        if existing is None:
            db.add(
                ProductVariant(
                    product_id=product.id,
                    color=spec.get("color"),
                    normalized_color=spec.get("normalized_color"),
                    size=spec.get("size"),
                    normalized_size=spec.get("normalized_size"),
                    sku=sku,
                    price=spec.get("price", base_price),
                    stock_quantity=spec.get("stock_quantity", 10),
                    reserved_quantity=0,
                    is_active=True,
                )
            )
            logger.info("Created demo variant: %s", sku)

    return product


def _get_or_create_customer(
    db: Session,
    shop_id: UUID,
    *,
    instagram_user_id: str,
    full_name: str,
    phone: str | None = None,
) -> Customer:
    customer = db.scalar(
        select(Customer).where(
            Customer.shop_id == shop_id,
            Customer.instagram_user_id == instagram_user_id,
        )
    )
    if customer is None:
        customer = Customer(
            shop_id=shop_id,
            instagram_user_id=instagram_user_id,
            full_name=full_name,
            phone=phone,
            city="Tehran",
        )
        db.add(customer)
        db.flush()
    return customer


def _get_or_create_conversation(
    db: Session,
    *,
    shop_id: UUID,
    account_id: UUID,
    customer_id: UUID,
    channel_conversation_id: str,
    **kwargs,
) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.shop_id == shop_id,
            Conversation.channel_conversation_id == channel_conversation_id,
        )
    )
    if conversation is None:
        conversation = Conversation(
            shop_id=shop_id,
            instagram_account_id=account_id,
            customer_id=customer_id,
            channel_conversation_id=channel_conversation_id,
            **kwargs,
        )
        db.add(conversation)
        db.flush()
    return conversation


def _ensure_message(
    db: Session,
    *,
    conversation_id: UUID,
    instagram_message_id: str,
    direction: MessageDirection,
    text: str,
    created_at: datetime | None = None,
) -> None:
    existing = db.scalar(select(Message).where(Message.instagram_message_id == instagram_message_id))
    if existing is not None:
        return
    message = Message(
        conversation_id=conversation_id,
        direction=direction,
        channel=MessageChannel.INSTAGRAM,
        message_type=MessageType.TEXT,
        text=text,
        instagram_message_id=instagram_message_id,
        raw_payload={},
    )
    if created_at is not None:
        message.created_at = created_at
    db.add(message)


def _ensure_order_with_item(
    db: Session,
    *,
    shop_id: UUID,
    customer_id: UUID,
    conversation_id: UUID,
    product: Product,
    variant: ProductVariant,
    status: OrderStatus,
    payment_status: OrderPaymentStatus,
    shipping_status: OrderShippingStatus,
    customer_name: str,
    reference_key: str,
) -> Order:
    existing = db.scalar(
        select(Order).where(
            Order.shop_id == shop_id,
            Order.notes == reference_key,
        )
    )
    if existing is not None:
        return existing

    order = Order(
        shop_id=shop_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        status=status,
        payment_status=payment_status,
        shipping_status=shipping_status,
        subtotal_amount=variant.price,
        total_amount=variant.price,
        currency="USD",
        customer_name=customer_name,
        phone="09121234567",
        city="Tehran",
        address="Valiasr St 10",
        postal_code="1234567890",
        notes=reference_key,
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_variant_id=variant.id,
            product_title_snapshot=product.title,
            variant_color_snapshot=variant.color,
            variant_size_snapshot=variant.size,
            sku_snapshot=variant.sku,
            quantity=1,
            unit_price=variant.price,
            total_price=variant.price,
        )
    )
    return order


def seed_rich_demo_data(db: Session, admin: User, shop: Shop, account: InstagramAccount) -> None:
    now = datetime.now(UTC)

    shop.agent_settings = {
        **(shop.agent_settings or {}),
        "auto_reply_enabled": True,
        "auto_send_enabled": False,
        "handoff_mode": "automatic",
        "default_language": "fa",
        "low_stock_threshold": 5,
        "preview_required_for_first_24h": False,
    }
    shop.onboarding_flags = {
        **(shop.onboarding_flags or {}),
        "dm_simulator": True,
        "demo_data_seeded": True,
    }

    agent_settings = db.get(ShopAgentSettings, shop.id)
    if agent_settings is None:
        db.add(
            ShopAgentSettings(
                shop_id=shop.id,
                mode=AgentMode.COPILOT,
                selling_style=SellingStyle.FRIENDLY,
                brand_voice="Warm, fashion-aware, concise Persian-first replies.",
                auto_send_enabled=False,
                preview_required_for_low_confidence=True,
                preview_required_for_first_order=True,
                preview_required_for_high_value_order=True,
                confidence_threshold_intent=Decimal("0.75"),
                confidence_threshold_product=Decimal("0.80"),
                confidence_threshold_variant=Decimal("0.85"),
                confidence_threshold_address=Decimal("0.80"),
                high_value_order_threshold=Decimal("500"),
            )
        )
        logger.info("Created shop agent studio settings")

    shops = ShopRepository(db)
    members = ShopMemberRepository(db)
    second_shop = shops.get_by_slug(SECOND_SHOP_SLUG)
    if second_shop is None:
        second_shop = Shop(name=SECOND_SHOP_NAME, slug=SECOND_SHOP_SLUG, default_currency="USD")
        shops.create(second_shop)
        members.create(ShopMember(shop_id=second_shop.id, user_id=admin.id, role=UserRole.OWNER))
        logger.info("Created second demo shop: %s", SECOND_SHOP_SLUG)

    black_shirt = db.scalar(
        select(Product).where(Product.shop_id == shop.id, Product.title == "Demo Black Shirt")
    )
    hoodie = _get_or_create_product(
        db,
        shop.id,
        title=HOODIE_TITLE,
        description="Cozy fleece hoodie for Instagram DM orders.",
        base_price=Decimal("59.99"),
        variants=[
            {
                "sku": "HD-BLK-L",
                "color": "Black",
                "normalized_color": "black",
                "size": "L",
                "normalized_size": "L",
                "stock_quantity": 12,
            },
            {
                "sku": "HD-BLK-M",
                "color": "Black",
                "normalized_color": "black",
                "size": "M",
                "normalized_size": "M",
                "stock_quantity": 3,
            },
            {
                "sku": "HD-NVY-L",
                "color": "Navy",
                "normalized_color": "navy",
                "size": "L",
                "normalized_size": "L",
                "stock_quantity": 8,
            },
        ],
    )
    dress = _get_or_create_product(
        db,
        shop.id,
        title=DRESS_TITLE,
        description="Light linen dress for summer campaigns.",
        base_price=Decimal("79.99"),
        variants=[
            {
                "sku": "DR-RED-S",
                "color": "Red",
                "normalized_color": "red",
                "size": "S",
                "normalized_size": "S",
                "stock_quantity": 6,
            },
            {
                "sku": "DR-RED-M",
                "color": "Red",
                "normalized_color": "red",
                "size": "M",
                "normalized_size": "M",
                "stock_quantity": 0,
            },
        ],
    )

    for alias in [
        ("مشکی", "black"),
        ("سیاه", "black"),
        ("قرمز", "red"),
        ("navy", "navy"),
    ]:
        if db.scalar(
            select(ColorAlias).where(
                ColorAlias.shop_id == shop.id,
                ColorAlias.raw_value == alias[0],
                ColorAlias.language == "und",
            )
        ) is None:
            db.add(
                ColorAlias(
                    shop_id=shop.id,
                    raw_value=alias[0],
                    normalized_value=alias[1],
                    language="und",
                )
            )

    for raw, normalized, category in [
        ("فری سایز", "FREE", None),
        ("medium", "M", "tops"),
        ("L", "L", None),
    ]:
        stmt = select(SizeAlias).where(
            SizeAlias.shop_id == shop.id,
            SizeAlias.raw_value == raw,
        )
        if category is None:
            stmt = stmt.where(SizeAlias.category.is_(None))
        else:
            stmt = stmt.where(SizeAlias.category == category)
        if db.scalar(stmt) is None:
            db.add(
                SizeAlias(
                    shop_id=shop.id,
                    raw_value=raw,
                    normalized_value=normalized,
                    category=category,
                )
            )

    for post_url, product, media_id in [
        (POST_URL_HOODIE, hoodie, "media-hoodie"),
        (POST_URL_DRESS, dress, "media-dress"),
    ]:
        if db.scalar(
            select(InstagramProductMap).where(
                InstagramProductMap.shop_id == shop.id,
                InstagramProductMap.instagram_post_url == post_url,
            )
        ) is None:
            db.add(
                InstagramProductMap(
                    shop_id=shop.id,
                    instagram_account_id=account.id,
                    instagram_media_id=media_id,
                    instagram_post_url=post_url,
                    product_id=product.id,
                    confidence_source=ConfidenceSource.MANUAL,
                    is_active=True,
                )
            )

    trigger_specs = [
        ("price", TriggerSourceType.COMMENT, "Thanks! I sent you pricing in DM. Which color and size?"),
        ("order", TriggerSourceType.DIRECT_DM, "Happy to help with your order — tell me color and size."),
        ("سایز", TriggerSourceType.STORY_REPLY, "Which size are you looking for?"),
    ]
    triggers: list[CommentToDmTrigger] = []
    for keyword, source_type, template in trigger_specs:
        trigger = db.scalar(
            select(CommentToDmTrigger).where(
                CommentToDmTrigger.shop_id == shop.id,
                CommentToDmTrigger.instagram_account_id == account.id,
                CommentToDmTrigger.keyword == keyword,
                CommentToDmTrigger.source_type == source_type,
            )
        )
        if trigger is None:
            trigger = CommentToDmTrigger(
                shop_id=shop.id,
                instagram_account_id=account.id,
                source_type=source_type,
                keyword=keyword,
                response_template=template,
                target_product_id=hoodie.id,
                is_active=True,
            )
            db.add(trigger)
            db.flush()
        triggers.append(trigger)

    hoodie_variant = db.scalar(
        select(ProductVariant).where(ProductVariant.product_id == hoodie.id, ProductVariant.sku == "HD-BLK-L")
    )
    shirt_variant = None
    if black_shirt is not None:
        shirt_variant = db.scalar(
            select(ProductVariant).where(
                ProductVariant.product_id == black_shirt.id,
                ProductVariant.sku == "DEMO-BLACK-L",
            )
        )

    ali = _get_or_create_customer(
        db, shop.id, instagram_user_id="demo-cust-ali", full_name="Ali Rezaei", phone="09121234567"
    )
    sara = _get_or_create_customer(
        db, shop.id, instagram_user_id="demo-cust-sara", full_name="Sara Karimi", phone="09129876543"
    )
    reza = _get_or_create_customer(
        db, shop.id, instagram_user_id="demo-cust-reza", full_name="Reza Ahmadi", phone="09121112222"
    )

    conv_order_ready = _get_or_create_conversation(
        db,
        shop_id=shop.id,
        account_id=account.id,
        customer_id=ali.id,
        channel_conversation_id="demo-conv-order-ready",
        state=ConversationState.OPEN,
        workflow_state=AgentWorkflowState.WAITING_FOR_CONFIRMATION,
        handoff_required=False,
        preview_required=True,
        priority_level=ConversationPriorityLevel.HIGH,
        priority_score=72,
        needs_attention=True,
        last_message_at=now - timedelta(minutes=12),
        assigned_operator_id=admin.id,
        suggested_outbound="سفارش شما آماده تایید است. مبلغ 59.99 دلار — تایید می‌کنید؟",
    )
    conv_handoff = _get_or_create_conversation(
        db,
        shop_id=shop.id,
        account_id=account.id,
        customer_id=sara.id,
        channel_conversation_id="demo-conv-handoff",
        state=ConversationState.PENDING_HANDOFF,
        workflow_state=AgentWorkflowState.HUMAN_HANDOFF,
        handoff_required=True,
        handoff_reason="low_confidence_variant",
        preview_required=True,
        priority_level=ConversationPriorityLevel.URGENT,
        priority_score=88,
        needs_attention=True,
        last_message_at=now - timedelta(minutes=4),
    )
    conv_sim = _get_or_create_conversation(
        db,
        shop_id=shop.id,
        account_id=account.id,
        customer_id=reza.id,
        channel_conversation_id="demo-conv-simulation",
        state=ConversationState.OPEN,
        workflow_state=AgentWorkflowState.IDLE,
        is_simulation=True,
        handoff_required=False,
        priority_level=ConversationPriorityLevel.LOW,
        priority_score=10,
        last_message_at=now - timedelta(hours=2),
    )

    _ensure_message(
        db,
        conversation_id=conv_order_ready.id,
        instagram_message_id="demo-msg-ali-in-1",
        direction=MessageDirection.INBOUND,
        text="این هودی مشکی سایز L می‌خوام",
        created_at=now - timedelta(minutes=20),
    )
    _ensure_message(
        db,
        conversation_id=conv_order_ready.id,
        instagram_message_id="demo-msg-ali-out-1",
        direction=MessageDirection.OUTBOUND,
        text="عالیه! لطفاً نام، تلفن و آدرس را بفرستید.",
        created_at=now - timedelta(minutes=18),
    )
    _ensure_message(
        db,
        conversation_id=conv_handoff.id,
        instagram_message_id="demo-msg-sara-in-1",
        direction=MessageDirection.INBOUND,
        text="Do you have this in XL?",
        created_at=now - timedelta(minutes=6),
    )
    _ensure_message(
        db,
        conversation_id=conv_sim.id,
        instagram_message_id="demo-msg-reza-in-1",
        direction=MessageDirection.INBOUND,
        text="تست شبیه‌ساز",
        created_at=now - timedelta(hours=2),
    )

    if db.scalar(select(ConversationSlots).where(ConversationSlots.conversation_id == conv_order_ready.id)) is None and hoodie_variant is not None:
        db.add(
            ConversationSlots(
                conversation_id=conv_order_ready.id,
                product_id=hoodie.id,
                product_variant_id=hoodie_variant.id,
                instagram_post_url=POST_URL_HOODIE,
                color="مشکی",
                normalized_color="black",
                size="L",
                normalized_size="L",
                quantity=1,
                customer_name="Ali Rezaei",
                phone="09121234567",
                city="Tehran",
                address="Valiasr St 10",
                postal_code="1234567890",
                missing_fields=[],
                confidence={"intent": 0.92, "product": 0.88, "variant": 0.91},
            )
        )

    if db.scalar(select(ConversationSlots).where(ConversationSlots.conversation_id == conv_handoff.id)) is None:
        db.add(
            ConversationSlots(
                conversation_id=conv_handoff.id,
                product_id=hoodie.id,
                color="XL",
                normalized_color="xl",
                quantity=1,
                missing_fields=["size", "address"],
                confidence={"intent": 0.7, "variant": 0.42},
            )
        )

    if hoodie_variant is not None:
        paid_order = _ensure_order_with_item(
            db,
            shop_id=shop.id,
            customer_id=ali.id,
            conversation_id=conv_order_ready.id,
            product=hoodie,
            variant=hoodie_variant,
            status=OrderStatus.PAID,
            payment_status=OrderPaymentStatus.PAID,
            shipping_status=OrderShippingStatus.PREPARING,
            customer_name="Ali Rezaei",
            reference_key="demo-order-paid-hoodie",
        )
        _ensure_order_with_item(
            db,
            shop_id=shop.id,
            customer_id=sara.id,
            conversation_id=conv_handoff.id,
            product=hoodie,
            variant=hoodie_variant,
            status=OrderStatus.WAITING_FOR_PAYMENT,
            payment_status=OrderPaymentStatus.PENDING,
            shipping_status=OrderShippingStatus.NOT_STARTED,
            customer_name="Sara Karimi",
            reference_key="demo-order-waiting-payment",
        )
        if shirt_variant is not None and black_shirt is not None:
            _ensure_order_with_item(
                db,
                shop_id=shop.id,
                customer_id=reza.id,
                conversation_id=conv_sim.id,
                product=black_shirt,
                variant=shirt_variant,
                status=OrderStatus.WAITING_FOR_CONFIRMATION,
                payment_status=OrderPaymentStatus.UNPAID,
                shipping_status=OrderShippingStatus.NOT_STARTED,
                customer_name="Reza Ahmadi",
                reference_key="demo-order-draft-shirt",
            )

        if db.scalar(
            select(SuggestedReply).where(
                SuggestedReply.conversation_id == conv_handoff.id,
                SuggestedReply.suggested_text.like("I can check%"),
            )
        ) is None:
            db.add(
                SuggestedReply(
                    shop_id=shop.id,
                    conversation_id=conv_handoff.id,
                    suggested_text="I can check alternative sizes for you — one moment.",
                    status=SuggestedReplyStatus.PENDING,
                    generated_by=SuggestedReplyGeneratedBy.AGENT,
                    reason="low_confidence_variant",
                )
            )

        price_trigger = triggers[0]
        if db.scalar(select(TriggerEvent).where(TriggerEvent.trigger_id == price_trigger.id).limit(1)) is None:
            db.add(
                TriggerEvent(
                    trigger_id=price_trigger.id,
                    conversation_id=conv_order_ready.id,
                    customer_id=ali.id,
                    matched_keyword="price",
                    source_type=TriggerSourceType.COMMENT,
                    dm_sent=True,
                    paid_order_id=paid_order.id,
                    revenue_amount=Decimal("59.99"),
                    created_at=now - timedelta(days=2),
                )
            )
            db.add(
                TriggerEvent(
                    trigger_id=price_trigger.id,
                    conversation_id=conv_handoff.id,
                    customer_id=sara.id,
                    matched_keyword="price",
                    source_type=TriggerSourceType.COMMENT,
                    dm_sent=True,
                    revenue_amount=Decimal("0"),
                    created_at=now - timedelta(days=1),
                )
            )

    if db.scalar(
        select(UnavailableDemandLog).where(
            UnavailableDemandLog.shop_id == shop.id,
            UnavailableDemandLog.reason == "out_of_stock",
        ).limit(1)
    ) is None:
        db.add(
            UnavailableDemandLog(
                shop_id=shop.id,
                product_id=dress.id,
                requested_color_raw="قرمز",
                requested_color_normalized="red",
                requested_size_raw="M",
                requested_size_normalized="M",
                requested_quantity=1,
                reason="out_of_stock",
                conversation_id=conv_handoff.id,
                customer_id=sara.id,
                estimated_lost_revenue=Decimal("79.99"),
            )
        )
        db.add(
            UnavailableDemandLog(
                shop_id=shop.id,
                product_id=hoodie.id,
                requested_color_raw="yellow",
                requested_color_normalized="yellow",
                requested_size_raw="L",
                requested_size_normalized="L",
                requested_quantity=2,
                reason="variant_not_found",
                estimated_lost_revenue=Decimal("119.98"),
            )
        )

    if account.status != InstagramAccountStatus.CONNECTED:
        account.status = InstagramAccountStatus.CONNECTED
    account.webhook_enabled = True

    db.flush()
    logger.info("Rich demo data seeded for shop %s", shop.slug)
