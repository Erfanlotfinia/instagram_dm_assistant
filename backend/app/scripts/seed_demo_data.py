"""Rich demo dataset for exercising all frontend features.

Called from app.scripts.seed after core admin/shop/catalog bootstrap.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import (
    AgentMode,
    AgentActionStatus,
    AgentRunStatus,
    AgentWorkflowState,
    CatalogAliasSource,
    CatalogImportJobStatus,
    ChannelAccountStatus,
    ChannelProvider,
    ConfidenceSource,
    ConversationEventType,
    ConversationPriorityLevel,
    ConversationState,
    FailedJobStatus,
    IncidentSeverity,
    IncidentStatus,
    IncidentTrigger,
    InstagramAccountStatus,
    MessageChannel,
    MessageDirection,
    MessageType,
    OrderPaymentStatus,
    OrderRecoveryStatus,
    OrderShippingStatus,
    OrderStatus,
    PaymentProvider,
    PaymentRecordStatus,
    ProductStatus,
    ScenarioPackType,
    SellingStyle,
    ShipmentProvider,
    ShipmentStatus,
    SimulatorRunSourceType,
    SimulatorRunStatus,
    SuggestedReplyGeneratedBy,
    SuggestedReplyStatus,
    TriggerSourceType,
    UpsellSuggestionStatus,
    UserRole,
    VariantAliasType,
)
from app.domain.models import (
    AbandonedOrderRecoveryRule,
    AdminAuditLog,
    AdminTask,
    AgentAction,
    AgentDecisionTrace,
    AgentRun,
    AutomationRuleSuggestion,
    CatalogImportJob,
    ChannelAccount,
    ColorAlias,
    CommentToDmTrigger,
    Conversation,
    ConversationEvent,
    ConversationSlots,
    Customer,
    CustomerPreferences,
    FailedJob,
    Incident,
    IncidentEvent,
    InstagramAccount,
    InstagramProductMap,
    Message,
    OperatorCorrection,
    Order,
    OrderItem,
    Payment,
    PolicyVersion,
    Product,
    ProductAlias,
    ProductNormalized,
    ProductUpsell,
    ProductVariant,
    ScenarioPack,
    Shipment,
    Shop,
    ShopAgentSettings,
    ShopMember,
    SimulatorRun,
    SimulatorRunItem,
    SizeAlias,
    SuggestedReply,
    TriggerEvent,
    UnavailableDemandLog,
    UpsellSuggestion,
    User,
    VariantAlias,
)
from app.repositories.shop_repository import ShopMemberRepository, ShopRepository
from app.services.conversation_event_service import EVENT_TITLES
from app.services.legacy_channel_compat import get_instagram_channel_account_id

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
        channel_account_id = get_instagram_channel_account_id(db, account_id)
        conversation = Conversation(
            shop_id=shop_id,
            instagram_account_id=account_id,
            channel_account_id=channel_account_id,
            channel_provider=ChannelProvider.INSTAGRAM.value,
            external_conversation_id=channel_conversation_id,
            channel_conversation_id=channel_conversation_id,
            customer_id=customer_id,
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
    existing = db.scalar(
        select(Message).where(Message.instagram_message_id == instagram_message_id)
    )
    if existing is not None:
        if created_at is not None:
            existing.created_at = created_at
        return
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    message = Message(
        shop_id=conversation.shop_id,
        conversation_id=conversation_id,
        customer_id=(
            conversation.customer_id if direction == MessageDirection.INBOUND else None
        ),
        channel_provider=ChannelProvider.INSTAGRAM,
        channel_account_id=conversation.channel_account_id,
        external_message_id=instagram_message_id,
        channel_message_id=instagram_message_id,
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


def _add_conversation_event(
    db: Session,
    *,
    conversation_id: UUID,
    event_type: ConversationEventType,
    created_at: datetime,
    description: str | None = None,
    metadata: dict | None = None,
    created_by_user_id: UUID | None = None,
) -> None:
    db.add(
        ConversationEvent(
            conversation_id=conversation_id,
            event_type=event_type,
            title=EVENT_TITLES[event_type],
            description=description,
            event_metadata=metadata,
            created_by_user_id=created_by_user_id,
            created_at=created_at,
        )
    )


def _conversation_has_events(db: Session, conversation_id: UUID) -> bool:
    return (
        db.scalar(
            select(ConversationEvent)
            .where(ConversationEvent.conversation_id == conversation_id)
            .limit(1)
        )
        is not None
    )


def _seed_conversation_events(
    db: Session,
    *,
    now: datetime,
    admin: User,
    conv_order_ready: Conversation,
    conv_handoff: Conversation,
    conv_sim: Conversation,
    hoodie: Product,
    hoodie_variant: ProductVariant | None,
) -> None:
    seeded = False

    if not _conversation_has_events(db, conv_order_ready.id):
        seeded = True
        _add_conversation_event(
            db,
            conversation_id=conv_order_ready.id,
            event_type=ConversationEventType.INBOUND_MESSAGE,
            description="این هودی مشکی سایز L می‌خوام",
            created_at=now - timedelta(minutes=20),
            metadata={"instagram_message_id": "demo-msg-ali-in-1"},
        )
        _add_conversation_event(
            db,
            conversation_id=conv_order_ready.id,
            event_type=ConversationEventType.PRODUCT_RESOLVED,
            description=hoodie.title,
            created_at=now - timedelta(minutes=19),
            metadata={"product_id": str(hoodie.id), "source": "instagram_post"},
        )
        if hoodie_variant is not None:
            _add_conversation_event(
                db,
                conversation_id=conv_order_ready.id,
                event_type=ConversationEventType.VARIANT_RESOLVED,
                description=f"{hoodie_variant.color} / {hoodie_variant.size}",
                created_at=now - timedelta(minutes=18, seconds=30),
                metadata={"variant_id": str(hoodie_variant.id), "sku": hoodie_variant.sku},
            )
            _add_conversation_event(
                db,
                conversation_id=conv_order_ready.id,
                event_type=ConversationEventType.INVENTORY_CHECKED,
                description="Variant in stock",
                created_at=now - timedelta(minutes=18),
                metadata={
                    "available_quantity": hoodie_variant.stock_quantity
                    - hoodie_variant.reserved_quantity
                },
            )
        _add_conversation_event(
            db,
            conversation_id=conv_order_ready.id,
            event_type=ConversationEventType.OUTBOUND_MESSAGE,
            description="عالیه! لطفاً نام، تلفن و آدرس را بفرستید.",
            created_at=now - timedelta(minutes=17),
        )
        _add_conversation_event(
            db,
            conversation_id=conv_order_ready.id,
            event_type=ConversationEventType.CUSTOMER_INFO_COMPLETED,
            description="Ali Rezaei · Tehran",
            created_at=now - timedelta(minutes=15),
        )
        _add_conversation_event(
            db,
            conversation_id=conv_order_ready.id,
            event_type=ConversationEventType.DRAFT_ORDER_CREATED,
            description="Draft order ready for confirmation",
            created_at=now - timedelta(minutes=14),
        )
        _add_conversation_event(
            db,
            conversation_id=conv_order_ready.id,
            event_type=ConversationEventType.CONFIRMATION_REQUESTED,
            description="Awaiting customer confirmation before payment",
            created_at=now - timedelta(minutes=13),
        )
        _add_conversation_event(
            db,
            conversation_id=conv_order_ready.id,
            event_type=ConversationEventType.CONVERSATION_ASSIGNED,
            description=admin.full_name,
            created_at=now - timedelta(minutes=12),
            created_by_user_id=admin.id,
            metadata={"operator_id": str(admin.id)},
        )
        _add_conversation_event(
            db,
            conversation_id=conv_order_ready.id,
            event_type=ConversationEventType.PAYMENT_RECEIVED,
            description="Order marked paid",
            created_at=now - timedelta(minutes=10),
        )

    if not _conversation_has_events(db, conv_handoff.id):
        seeded = True
        _add_conversation_event(
            db,
            conversation_id=conv_handoff.id,
            event_type=ConversationEventType.INBOUND_MESSAGE,
            description="Do you have this in XL?",
            created_at=now - timedelta(minutes=6),
            metadata={"instagram_message_id": "demo-msg-sara-in-1"},
        )
        _add_conversation_event(
            db,
            conversation_id=conv_handoff.id,
            event_type=ConversationEventType.PRODUCT_RESOLVED,
            description=hoodie.title,
            created_at=now - timedelta(minutes=5, seconds=30),
            metadata={"product_id": str(hoodie.id)},
        )
        _add_conversation_event(
            db,
            conversation_id=conv_handoff.id,
            event_type=ConversationEventType.HANDOFF_REQUIRED,
            description="Variant confidence below threshold (0.42)",
            created_at=now - timedelta(minutes=5),
            metadata={"reason": "low_confidence_variant"},
        )
        _add_conversation_event(
            db,
            conversation_id=conv_handoff.id,
            event_type=ConversationEventType.SUGGESTED_REPLY_CREATED,
            description="I can check alternative sizes for you — one moment.",
            created_at=now - timedelta(minutes=4),
        )

    if not _conversation_has_events(db, conv_sim.id):
        seeded = True
        _add_conversation_event(
            db,
            conversation_id=conv_sim.id,
            event_type=ConversationEventType.INBOUND_MESSAGE,
            description="تست شبیه‌ساز",
            created_at=now - timedelta(hours=2),
            metadata={"instagram_message_id": "demo-msg-reza-in-1", "is_simulation": True},
        )

    if seeded:
        logger.info("Seeded demo conversation events for activity timeline")


def _seed_dress_inquiry_events(
    db: Session,
    *,
    now: datetime,
    dress: Product,
    dress_variant: ProductVariant | None,
) -> None:
    conv_dress = db.scalar(
        select(Conversation).where(
            Conversation.channel_conversation_id == "demo-conv-dress-inquiry"
        )
    )
    if conv_dress is None or _conversation_has_events(db, conv_dress.id):
        return

    _add_conversation_event(
        db,
        conversation_id=conv_dress.id,
        event_type=ConversationEventType.INBOUND_MESSAGE,
        description="Is the red dress available in S?",
        created_at=now - timedelta(hours=6),
        metadata={"instagram_message_id": "demo-msg-nadia-in-1"},
    )
    _add_conversation_event(
        db,
        conversation_id=conv_dress.id,
        event_type=ConversationEventType.PRODUCT_RESOLVED,
        description=dress.title,
        created_at=now - timedelta(hours=5, minutes=55),
        metadata={"product_id": str(dress.id), "source": "instagram_post"},
    )
    if dress_variant is not None:
        _add_conversation_event(
            db,
            conversation_id=conv_dress.id,
            event_type=ConversationEventType.VARIANT_RESOLVED,
            description=f"{dress_variant.color} / {dress_variant.size}",
            created_at=now - timedelta(hours=5, minutes=50),
            metadata={"variant_id": str(dress_variant.id), "sku": dress_variant.sku},
        )
        _add_conversation_event(
            db,
            conversation_id=conv_dress.id,
            event_type=ConversationEventType.INVENTORY_CHECKED,
            description="Variant in stock",
            created_at=now - timedelta(hours=5, minutes=48),
            metadata={
                "available_quantity": dress_variant.stock_quantity - dress_variant.reserved_quantity
            },
        )
    _add_conversation_event(
        db,
        conversation_id=conv_dress.id,
        event_type=ConversationEventType.INBOUND_MESSAGE,
        description="Perfect, I'll take it",
        created_at=now - timedelta(hours=5, minutes=45),
        metadata={"instagram_message_id": "demo-msg-nadia-in-2"},
    )
    _add_conversation_event(
        db,
        conversation_id=conv_dress.id,
        event_type=ConversationEventType.CUSTOMER_INFO_COMPLETED,
        description="Nadia Hosseini · awaiting shipping details",
        created_at=now - timedelta(hours=5, minutes=30),
    )
    logger.info("Seeded demo conversation events for dress inquiry timeline")


def _seed_dashboard_metrics_demo(
    db: Session,
    *,
    shop: Shop,
    account: InstagramAccount,
    now: datetime,
    hoodie: Product,
    dress: Product,
    black_shirt: Product | None,
    hoodie_variant: ProductVariant | None,
    dress_variant: ProductVariant | None,
    shirt_variant: ProductVariant | None,
    ali: Customer,
    sara: Customer,
    reza: Customer,
    conv_order_ready: Conversation,
    conv_handoff: Conversation,
    conv_sim: Conversation,
) -> None:
    """Extra conversations, orders, and upsells so dashboard funnel/recovery widgets look alive."""
    if (
        db.scalar(
            select(Order).where(
                Order.shop_id == shop.id,
                Order.notes == "demo-order-recovered-hoodie",
            )
        )
        is not None
    ):
        return

    nadia = _get_or_create_customer(
        db,
        shop.id,
        instagram_user_id="demo-cust-nadia",
        full_name="Nadia Hosseini",
        phone="09123334444",
    )
    conv_dress = _get_or_create_conversation(
        db,
        shop_id=shop.id,
        account_id=account.id,
        customer_id=nadia.id,
        channel_conversation_id="demo-conv-dress-inquiry",
        state=ConversationState.OPEN,
        workflow_state=AgentWorkflowState.WAITING_FOR_CUSTOMER_INFO,
        handoff_required=False,
        priority_level=ConversationPriorityLevel.MEDIUM,
        priority_score=45,
        last_message_at=now - timedelta(hours=5),
    )

    for message_id, conversation_id, text, created_at in [
        (
            "demo-msg-ali-in-2",
            conv_order_ready.id,
            "آدرس همینه که قبلاً فرستادم",
            now - timedelta(minutes=15),
        ),
        (
            "demo-msg-sara-in-2",
            conv_handoff.id,
            "What colors do you have?",
            now - timedelta(minutes=5),
        ),
        ("demo-msg-sara-in-3", conv_handoff.id, "Maybe navy instead?", now - timedelta(minutes=3)),
        ("demo-msg-reza-in-2", conv_sim.id, "قیمت چنده؟", now - timedelta(hours=1, minutes=50)),
        (
            "demo-msg-nadia-in-1",
            conv_dress.id,
            "Is the red dress available in S?",
            now - timedelta(hours=6),
        ),
        (
            "demo-msg-nadia-in-2",
            conv_dress.id,
            "Perfect, I'll take it",
            now - timedelta(hours=5, minutes=45),
        ),
    ]:
        _ensure_message(
            db,
            conversation_id=conversation_id,
            instagram_message_id=message_id,
            direction=MessageDirection.INBOUND,
            text=text,
            created_at=created_at,
        )

    if (
        db.scalar(
            select(ConversationSlots).where(ConversationSlots.conversation_id == conv_dress.id)
        )
        is None
    ):
        db.add(
            ConversationSlots(
                conversation_id=conv_dress.id,
                product_id=dress.id,
                product_variant_id=dress_variant.id if dress_variant is not None else None,
                instagram_post_url=POST_URL_DRESS,
                color="Red",
                normalized_color="red",
                size="S",
                normalized_size="S",
                quantity=1,
                missing_fields=[],
                confidence={"intent": 0.9, "product": 0.86, "variant": 0.88},
            )
        )

    if (
        black_shirt is not None
        and db.scalar(
            select(ConversationSlots).where(ConversationSlots.conversation_id == conv_sim.id)
        )
        is None
    ):
        db.add(
            ConversationSlots(
                conversation_id=conv_sim.id,
                product_id=black_shirt.id,
                product_variant_id=shirt_variant.id if shirt_variant is not None else None,
                color="Black",
                normalized_color="black",
                size="L",
                normalized_size="L",
                quantity=1,
                missing_fields=["address"],
                confidence={"intent": 0.82, "product": 0.79, "variant": 0.8},
            )
        )

    if hoodie_variant is None or dress_variant is None:
        return

    _ensure_order_with_item(
        db,
        shop_id=shop.id,
        customer_id=nadia.id,
        conversation_id=conv_dress.id,
        product=dress,
        variant=dress_variant,
        status=OrderStatus.EXPIRED,
        payment_status=OrderPaymentStatus.UNPAID,
        shipping_status=OrderShippingStatus.NOT_STARTED,
        customer_name="Nadia Hosseini",
        reference_key="demo-order-expired-dress",
        recovery_status=OrderRecoveryStatus.ELIGIBLE,
    )
    _ensure_order_with_item(
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
        reference_key="demo-order-recovered-hoodie",
        recovery_status=OrderRecoveryStatus.RECOVERED,
    )

    upsell_rule = db.scalar(
        select(ProductUpsell).where(
            ProductUpsell.shop_id == shop.id,
            ProductUpsell.source_product_id == hoodie.id,
            ProductUpsell.target_product_id == dress.id,
        )
    )
    if upsell_rule is None:
        upsell_rule = ProductUpsell(
            shop_id=shop.id,
            source_product_id=hoodie.id,
            target_product_id=dress.id,
            message_template="Customers also love our {target_product} — want to add one?",
            is_active=True,
        )
        db.add(upsell_rule)
        db.flush()

    upsell_specs = [
        (conv_order_ready.id, ali.id, UpsellSuggestionStatus.ACCEPTED, "demo-upsell-accepted"),
        (
            conv_handoff.id,
            sara.id,
            UpsellSuggestionStatus.SUGGESTED,
            "demo-upsell-suggested-handoff",
        ),
        (conv_sim.id, reza.id, UpsellSuggestionStatus.SUGGESTED, "demo-upsell-suggested-sim"),
        (conv_dress.id, nadia.id, UpsellSuggestionStatus.SUGGESTED, "demo-upsell-suggested-dress"),
    ]
    for conversation_id, _customer_id, status, marker in upsell_specs:
        if (
            db.scalar(
                select(UpsellSuggestion).where(
                    UpsellSuggestion.shop_id == shop.id,
                    UpsellSuggestion.suggested_text.like(f"%{marker}%"),
                )
            )
            is not None
        ):
            continue
        db.add(
            UpsellSuggestion(
                shop_id=shop.id,
                conversation_id=conversation_id,
                source_product_id=hoodie.id,
                target_product_id=dress.id,
                suggested_text=f"{marker}: Pair the hoodie with our linen dress?",
                status=status,
            )
        )

    logger.info("Seeded dashboard funnel, recovery, and upsell demo metrics")


def _ensure_auto_sent_audit_for_traces(db: Session, shop_id: UUID) -> None:
    """Backfill message_auto_sent audit rows for auto-send decision traces."""
    traces = db.scalars(
        select(AgentDecisionTrace)
        .join(Conversation, Conversation.id == AgentDecisionTrace.conversation_id)
        .where(
            Conversation.shop_id == shop_id,
            Conversation.is_simulation.is_(False),
            AgentDecisionTrace.auto_send_allowed.is_(True),
            AgentDecisionTrace.human_handoff_required.is_(False),
        )
    ).all()
    for trace in traces:
        seed_key = f"trace-{trace.id}"
        existing = db.scalar(
            select(AdminAuditLog).where(
                AdminAuditLog.shop_id == shop_id,
                AdminAuditLog.action == "message_auto_sent",
                AdminAuditLog.details.contains({"seed_key": seed_key}),
            ).limit(1)
        )
        if existing is not None:
            existing.created_at = trace.created_at
            continue
        log = AdminAuditLog(
            shop_id=shop_id,
            action="message_auto_sent",
            entity_type="conversation",
            entity_id=str(trace.conversation_id),
            details={
                "seed": True,
                "seed_analytics": True,
                "seed_key": seed_key,
                "message_id": str(trace.message_id),
            },
        )
        log.created_at = trace.created_at
        db.add(log)


def _seed_analytics_signals(
    db: Session,
    *,
    shop: Shop,
    now: datetime,
    conv_order_ready: Conversation,
    conv_handoff: Conversation,
) -> None:
    """Audit logs and outbound replies so analytics overview KPIs have demo values."""
    outbound_specs = [
        (
            "demo-msg-sara-out-1",
            conv_handoff.id,
            "Let me check XL availability with our team.",
            now - timedelta(minutes=4, seconds=30),
        ),
    ]
    for message_id, conversation_id, text, created_at in outbound_specs:
        _ensure_message(
            db,
            conversation_id=conversation_id,
            instagram_message_id=message_id,
            direction=MessageDirection.OUTBOUND,
            text=text,
            created_at=created_at,
        )

    if (
        db.scalar(
            select(AdminAuditLog.id).where(
                AdminAuditLog.shop_id == shop.id,
                AdminAuditLog.details.contains({"seed_analytics": True}),
            ).limit(1)
        )
        is None
    ):
        audit_specs = [
            ("message_auto_sent", str(conv_order_ready.id), now - timedelta(minutes=17)),
            ("message_auto_sent", str(conv_order_ready.id), now - timedelta(minutes=16)),
            ("message_auto_sent", str(conv_handoff.id), now - timedelta(minutes=4)),
        ]
        for action, entity_id, created_at in audit_specs:
            log = AdminAuditLog(
                shop_id=shop.id,
                action=action,
                entity_type="conversation",
                entity_id=entity_id,
                details={"seed": True, "seed_analytics": True},
            )
            log.created_at = created_at
            db.add(log)

    _ensure_auto_sent_audit_for_traces(db, shop.id)


def _trends_window_start(now: datetime, days: int = 30) -> datetime:
    return (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)


def _trends_day_volume(day_offset: int, window_start: datetime) -> int:
    weekday = (window_start + timedelta(days=day_offset)).weekday()
    weekend_factor = 0.55 if weekday >= 5 else 1.0
    campaign = 1.35 if 8 <= day_offset <= 22 else 1.0
    growth = 0.9 + (day_offset / 29) * 0.55
    wave = 1.0 + (((day_offset * 5) % 9) - 4) * 0.035
    base = 34 + (day_offset % 7) * 5 + ((day_offset * 11 + 5) % 16)
    return max(30, int(base * weekend_factor * growth * campaign * wave))


def _trends_message_time(day_start: datetime, index: int) -> datetime:
    return day_start + timedelta(
        hours=8 + (index * 5) % 14,
        minutes=(index * 13) % 60,
        seconds=(index * 7) % 60,
    )


def _trends_trace_outcome(
    trace_index: int,
    day_offset: int,
) -> tuple[bool, bool, AgentWorkflowState, str, dict[str, Any]]:
    """Deterministic mix: ~48% automated, ~32% LLM, ~20% handoff with varied intents."""
    cycle = [
        (True, False, AgentWorkflowState.WAITING_FOR_CONFIRMATION, "buy_product", {"intent": 0.91, "product": 0.88, "variant": 0.89, "risk_level": "low"}),
        (True, False, AgentWorkflowState.WAITING_FOR_PAYMENT, "ask_price", {"intent": 0.88, "product": 0.86, "variant": 0.86, "risk_level": "low"}),
        (True, False, AgentWorkflowState.WAITING_FOR_CUSTOMER_INFO, "ask_size", {"intent": 0.87, "product": 0.85, "variant": 0.9, "risk_level": "low"}),
        (False, False, AgentWorkflowState.IDLE, "ask_availability", {"intent": 0.76, "product": 0.74, "variant": 0.72, "risk_level": "medium"}),
        (False, False, AgentWorkflowState.WAITING_FOR_CUSTOMER_INFO, "confirm_order", {"intent": 0.74, "product": 0.72, "variant": 0.7, "risk_level": "medium"}),
        (False, False, AgentWorkflowState.IDLE, "general_question", {"intent": 0.71, "product": 0.69, "variant": 0.68, "risk_level": "medium"}),
        (False, True, AgentWorkflowState.HUMAN_HANDOFF, "buy_product", {"intent": 0.69, "product": 0.58, "variant": 0.41, "risk_level": "high", "risk_reasons": ["low_variant_confidence"]}),
        (False, True, AgentWorkflowState.HUMAN_HANDOFF, "payment_support", {"intent": 0.66, "product": 0.62, "variant": 0.55, "risk_level": "high", "risk_reasons": ["payment_dispute"]}),
        (True, False, AgentWorkflowState.WAITING_FOR_CONFIRMATION, "buy_product", {"intent": 0.93, "product": 0.91, "variant": 0.92, "risk_level": "low"}),
        (False, False, AgentWorkflowState.IDLE, "ask_shipping", {"intent": 0.78, "product": 0.76, "variant": 0.75, "risk_level": "medium"}),
    ]
    idx = (trace_index + day_offset * 3) % len(cycle)
    auto_send, handoff_required, next_state, intent, risk = cycle[idx]
    if day_offset >= 20 and not handoff_required:
        auto_send = trace_index % 4 != 0
    return auto_send, handoff_required, next_state, intent, risk


def _add_trend_decision_trace(
    db: Session,
    *,
    conversation: Conversation,
    message: Message,
    hoodie: Product,
    hoodie_variant: ProductVariant,
    trace_time: datetime,
    trace_index: int,
    day_offset: int,
) -> None:
    auto_send, handoff_required, next_state, intent, risk_score = _trends_trace_outcome(
        trace_index,
        day_offset,
    )
    agent_run = AgentRun(
        conversation_id=conversation.id,
        input_message_id=message.id,
        model_name="demo-trend-agent",
        prompt_version="seed-trend-v2",
        input_json={"message_text": message.text},
        output_json={
            "intent": intent,
            "confidence": {
                "intent": float(risk_score.get("intent", 0.8)),
                "product": float(risk_score.get("product", 0.78)),
                "variant": float(risk_score.get("variant", 0.86)),
            },
        },
        status=AgentRunStatus.SUCCESS,
        is_simulation=False,
    )
    agent_run.created_at = trace_time - timedelta(seconds=20)
    db.add(agent_run)
    db.flush()

    trace = AgentDecisionTrace(
        conversation_id=conversation.id,
        message_id=message.id,
        agent_run_id=agent_run.id,
        intent=intent,
        extracted_slots={"color": "black", "size": "M"},
        normalized_slots={"color": "black", "size": "M"},
        product_candidates=[{"product_id": str(hoodie.id), "title": hoodie.title, "score": 0.85}],
        selected_product_id=hoodie.id,
        variant_resolution={
            "variant_id": str(hoodie_variant.id),
            "sku": hoodie_variant.sku,
            "confidence": float(risk_score.get("variant", 0.86)),
        },
        inventory_result={"available": True},
        risk_score=risk_score,
        order_action={"order_id": None, "status": None},
        next_state=next_state.value,
        auto_send_allowed=auto_send,
        human_handoff_required=handoff_required,
        reasoning_summary=(
            f"Automated reply sent for {intent.replace('_', ' ')}."
            if auto_send
            else f"Routed to {'operator' if handoff_required else 'LLM review'} for {intent.replace('_', ' ')}."
        ),
    )
    trace.created_at = trace_time
    db.add(trace)


def _ensure_trend_day(
    db: Session,
    *,
    offset: int,
    window_start: datetime,
    conversations: list[Conversation],
    hoodie: Product,
    hoodie_variant: ProductVariant,
) -> None:
    """Ensure a full day of inbound messages and decision traces for dashboard charts."""
    day_start = window_start + timedelta(days=offset)
    volume = _trends_day_volume(offset, window_start)

    for i in range(volume):
        message_key = f"demo-trend-msg-{offset}-{i}"
        message = db.scalar(select(Message).where(Message.instagram_message_id == message_key))
        msg_time = _trends_message_time(day_start, i)
        if message is None:
            conv = conversations[(offset + i) % len(conversations)]
            _ensure_message(
                db,
                conversation_id=conv.id,
                instagram_message_id=message_key,
                direction=MessageDirection.INBOUND,
                text=f"Customer message day {offset + 1} #{i + 1}",
                created_at=msg_time,
            )
            message = db.scalar(select(Message).where(Message.instagram_message_id == message_key))
        else:
            message.created_at = msg_time

        if message is None:
            continue

        trace_time = msg_time + timedelta(minutes=2 + (i % 5))
        trace = db.scalar(
            select(AgentDecisionTrace).where(AgentDecisionTrace.message_id == message.id).limit(1)
        )
        if trace is None:
            conversation = db.get(Conversation, message.conversation_id)
            if conversation is None:
                continue
            _add_trend_decision_trace(
                db,
                conversation=conversation,
                message=message,
                hoodie=hoodie,
                hoodie_variant=hoodie_variant,
                trace_time=trace_time,
                trace_index=i,
                day_offset=offset,
            )
        else:
            trace.created_at = trace_time
            if trace.agent_run_id is not None:
                agent_run = db.get(AgentRun, trace.agent_run_id)
                if agent_run is not None:
                    agent_run.created_at = trace_time - timedelta(seconds=20)


def _ensure_trend_conversations(
    db: Session,
    *,
    shop: Shop,
    account: InstagramAccount,
    reza: Customer,
    now: datetime,
) -> list[Conversation]:
    trend_customers = [
        reza,
        _get_or_create_customer(
            db,
            shop.id,
            instagram_user_id="demo-cust-trend-a",
            full_name="Trend Customer A",
            phone="09124445566",
        ),
        _get_or_create_customer(
            db,
            shop.id,
            instagram_user_id="demo-cust-trend-b",
            full_name="Trend Customer B",
            phone="09125556677",
        ),
        _get_or_create_customer(
            db,
            shop.id,
            instagram_user_id="demo-cust-trend-c",
            full_name="Trend Customer C",
            phone="09126667788",
        ),
        _get_or_create_customer(
            db,
            shop.id,
            instagram_user_id="demo-cust-trend-d",
            full_name="Trend Customer D",
            phone="09127778899",
        ),
        _get_or_create_customer(
            db,
            shop.id,
            instagram_user_id="demo-cust-trend-e",
            full_name="Trend Customer E",
            phone="09128889900",
        ),
    ]
    conversations: list[Conversation] = []
    for idx, customer in enumerate(trend_customers):
        conversations.append(
            _get_or_create_conversation(
                db,
                shop_id=shop.id,
                account_id=account.id,
                customer_id=customer.id,
                channel_conversation_id=f"demo-conv-trends-history-{idx}",
                state=ConversationState.CLOSED if idx == 0 else ConversationState.OPEN,
                workflow_state=AgentWorkflowState.IDLE,
                handoff_required=False,
                last_message_at=now - timedelta(days=1),
            )
        )
    return conversations


def _ensure_trend_commerce_for_day(
    db: Session,
    *,
    offset: int,
    day_start: datetime,
    shop: Shop,
    conversations: list[Conversation],
    trend_customers: list[Customer],
    hoodie: Product,
    hoodie_variant: ProductVariant,
) -> None:
    customer = trend_customers[offset % len(trend_customers)]
    conversation = conversations[offset % len(conversations)]

    if offset % 3 == 0:
        order = _ensure_order_with_item(
            db,
            shop_id=shop.id,
            customer_id=customer.id,
            conversation_id=conversation.id,
            product=hoodie,
            variant=hoodie_variant,
            status=OrderStatus.PAID,
            payment_status=OrderPaymentStatus.PAID,
            shipping_status=OrderShippingStatus.DELIVERED,
            customer_name=customer.full_name or "Trend Customer",
            reference_key=f"demo-trend-order-{offset}",
        )
        order.created_at = day_start + timedelta(hours=16)

    if offset % 4 in (1, 3):
        pending = _ensure_order_with_item(
            db,
            shop_id=shop.id,
            customer_id=customer.id,
            conversation_id=conversation.id,
            product=hoodie,
            variant=hoodie_variant,
            status=OrderStatus.PAYMENT_PENDING,
            payment_status=OrderPaymentStatus.UNPAID,
            shipping_status=OrderShippingStatus.NOT_STARTED,
            customer_name=customer.full_name or "Trend Customer",
            reference_key=f"demo-trend-pending-{offset}",
        )
        pending.created_at = day_start + timedelta(hours=11, minutes=30)


def _refresh_dashboard_trends_history(
    db: Session,
    *,
    now: datetime,
    shop: Shop,
    account: InstagramAccount,
    reza: Customer,
    hoodie: Product,
    hoodie_variant: ProductVariant,
) -> None:
    """Re-anchor demo trend messages/traces and backfill missing decision traces."""
    window_start = _trends_window_start(now)
    trend_conversations = _ensure_trend_conversations(
        db,
        shop=shop,
        account=account,
        reza=reza,
        now=now,
    )
    trend_customers = [
        db.get(Customer, conversation.customer_id)
        for conversation in trend_conversations
        if conversation.customer_id is not None
    ]
    trend_customers = [customer for customer in trend_customers if customer is not None]

    for offset in range(30):
        day_start = window_start + timedelta(days=offset)
        _ensure_trend_day(
            db,
            offset=offset,
            window_start=window_start,
            conversations=trend_conversations,
            hoodie=hoodie,
            hoodie_variant=hoodie_variant,
        )
        if trend_customers:
            _ensure_trend_commerce_for_day(
                db,
                offset=offset,
                day_start=day_start,
                shop=shop,
                conversations=trend_conversations,
                trend_customers=trend_customers,
                hoodie=hoodie,
                hoodie_variant=hoodie_variant,
            )

    conv_ids = {conversation.id for conversation in trend_conversations}
    for conv_id in conv_ids:
        conversation = db.get(Conversation, conv_id)
        if conversation is None:
            continue
        latest = db.scalar(
            select(Message.created_at)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        if latest is not None:
            conversation.last_message_at = latest

    logger.info("Refreshed and backfilled 30-day AI decision trend history")


def _seed_agent_run_failures(
    db: Session,
    *,
    conv_handoff: Conversation,
    conv_sim: Conversation,
    now: datetime,
) -> None:
    """Failed LLM runs so AI Control safety KPIs show realistic non-zero values."""
    failure_specs = [
        (
            "demo-fail-msg-1",
            conv_handoff.id,
            "Invalid JSON response: unexpected token at position 14",
            now - timedelta(days=1, hours=3),
        ),
        (
            "demo-fail-msg-2",
            conv_handoff.id,
            "Schema validation failed: missing required field 'intent'",
            now - timedelta(days=4, hours=2),
        ),
        (
            "demo-fail-msg-3",
            conv_sim.id,
            "OpenAI request timed out after 30s",
            now - timedelta(days=9, hours=5),
        ),
        (
            "demo-fail-msg-4",
            conv_handoff.id,
            "Invalid JSON response: unexpected end of input",
            now - timedelta(days=15, hours=1),
        ),
        (
            "demo-fail-msg-5",
            conv_handoff.id,
            "Model returned empty completion",
            now - timedelta(days=22, hours=4),
        ),
        (
            "demo-fail-msg-6",
            conv_sim.id,
            "Invalid JSON response: trailing comma in slots object",
            now - timedelta(days=27, hours=6),
        ),
    ]
    for message_id, conversation_id, error_message, created_at in failure_specs:
        existing_run = db.scalar(
            select(AgentRun)
            .join(Message, Message.id == AgentRun.input_message_id)
            .where(Message.instagram_message_id == message_id)
            .limit(1)
        )
        if existing_run is not None:
            existing_run.status = AgentRunStatus.FAILED
            existing_run.error_message = error_message
            existing_run.created_at = created_at
            continue

        _ensure_message(
            db,
            conversation_id=conversation_id,
            instagram_message_id=message_id,
            direction=MessageDirection.INBOUND,
            text="Message that triggered a failed agent run",
            created_at=created_at - timedelta(minutes=1),
        )
        message = db.scalar(select(Message).where(Message.instagram_message_id == message_id))
        if message is None:
            continue
        run = AgentRun(
            conversation_id=conversation_id,
            input_message_id=message.id,
            model_name="demo-failure-agent",
            prompt_version="seed-fail-v1",
            input_json={"message_text": message.text},
            output_json={},
            status=AgentRunStatus.FAILED,
            error_message=error_message,
            is_simulation=False,
        )
        run.created_at = created_at
        db.add(run)

    logger.info("Seeded failed agent runs for AI control metrics")


def _seed_dashboard_trends_history(
    db: Session,
    *,
    shop: Shop,
    account: InstagramAccount,
    now: datetime,
    hoodie: Product,
    hoodie_variant: ProductVariant | None,
    reza: Customer,
) -> None:
    """Spread inbound messages, decision traces, and paid orders across the last 30 days."""
    if hoodie_variant is None:
        return

    if (
        db.scalar(
            select(Message).where(Message.instagram_message_id == "demo-trend-msg-0-0")
        )
        is not None
    ):
        _refresh_dashboard_trends_history(
            db,
            now=now,
            shop=shop,
            account=account,
            reza=reza,
            hoodie=hoodie,
            hoodie_variant=hoodie_variant,
        )
        return

    window_start = _trends_window_start(now)
    days = 30
    conversations = _ensure_trend_conversations(
        db,
        shop=shop,
        account=account,
        reza=reza,
        now=now,
    )
    trend_customers = [
        db.get(Customer, conversation.customer_id)
        for conversation in conversations
        if conversation.customer_id is not None
    ]
    trend_customers = [customer for customer in trend_customers if customer is not None]

    for offset in range(days):
        day_start = window_start + timedelta(days=offset)
        _ensure_trend_day(
            db,
            offset=offset,
            window_start=window_start,
            conversations=conversations,
            hoodie=hoodie,
            hoodie_variant=hoodie_variant,
        )
        if trend_customers:
            _ensure_trend_commerce_for_day(
                db,
                offset=offset,
                day_start=day_start,
                shop=shop,
                conversations=conversations,
                trend_customers=trend_customers,
                hoodie=hoodie,
                hoodie_variant=hoodie_variant,
            )

    logger.info("Seeded 30-day dashboard and AI decision chart history")


def _seed_failed_jobs(
    db: Session,
    *,
    shop: Shop,
    account: InstagramAccount,
    conv_order_ready: Conversation,
    conv_handoff: Conversation,
    ali: Customer,
    sara: Customer,
) -> None:
    if (
        db.scalar(select(FailedJob).where(FailedJob.error_message.like("demo:%")).limit(1))
        is not None
    ):
        return

    inbound_order = db.scalar(
        select(Message).where(Message.instagram_message_id == "demo-msg-ali-in-1")
    )
    inbound_handoff = db.scalar(
        select(Message).where(Message.instagram_message_id == "demo-msg-sara-in-1")
    )
    now = datetime.now(UTC)
    settings_queue = "channel.message.received"
    dlq_queue = "channel.message.received.dlq"

    if inbound_order is not None:
        db.add(
            FailedJob(
                shop_id=shop.id,
                queue_name=settings_queue,
                job_type="message_received",
                payload={
                    "message_id": str(inbound_order.id),
                    "conversation_id": str(conv_order_ready.id),
                    "shop_id": str(shop.id),
                    "instagram_account_id": str(account.id),
                    "customer_id": str(ali.id),
                },
                error_message="demo: ConversationOrchestrator timed out waiting for OpenAI response",
                traceback="TimeoutError: LLM request exceeded 30s",
                retry_count=3,
                max_retries=3,
                status=FailedJobStatus.FAILED,
                resolved=False,
                created_at=now - timedelta(minutes=12),
            )
        )

    if inbound_handoff is not None:
        db.add(
            FailedJob(
                shop_id=shop.id,
                queue_name=dlq_queue,
                job_type="message_received",
                payload={
                    "message_id": str(inbound_handoff.id),
                    "conversation_id": str(conv_handoff.id),
                    "shop_id": str(shop.id),
                    "instagram_account_id": str(account.id),
                    "customer_id": str(sara.id),
                },
                error_message="demo: Variant lock could not be acquired after max retries",
                traceback="ConversationLockedError: Conversation lock held by another worker",
                retry_count=3,
                max_retries=3,
                status=FailedJobStatus.FAILED,
                resolved=False,
                created_at=now - timedelta(minutes=5),
            )
        )

    db.add(
        FailedJob(
            shop_id=None,
            queue_name=dlq_queue,
            job_type="message_received",
            payload={"raw": "malformed-worker-payload", "retry_count": 3},
            error_message="demo: Worker payload failed JSON schema validation",
            traceback="ValidationError: 3 validation errors for MessageReceivedJob\nmessage_id\n  field required",
            retry_count=3,
            max_retries=3,
            status=FailedJobStatus.FAILED,
            resolved=False,
            created_at=now - timedelta(minutes=2),
        )
    )
    logger.info("Seeded demo failed jobs for system health UI")


def _seed_recovery_rule(db: Session, shop_id: UUID) -> None:
    if (
        db.scalar(
            select(AbandonedOrderRecoveryRule)
            .where(AbandonedOrderRecoveryRule.shop_id == shop_id)
            .limit(1)
        )
        is not None
    ):
        return
    db.add(
        AbandonedOrderRecoveryRule(
            shop_id=shop_id,
            trigger_after_minutes=60,
            max_attempts=2,
            message_template=(
                "Hi {customer_name}, your order ({order_total} {currency}) is still waiting for payment. "
                "Reply here if you need help completing checkout."
            ),
            is_active=True,
        )
    )
    logger.info("Seeded abandoned-order recovery rule")


def _seed_decision_traces(
    db: Session,
    *,
    conv_order_ready: Conversation,
    conv_handoff: Conversation,
    hoodie: Product,
    hoodie_variant: ProductVariant | None,
) -> None:
    specs = [
        (
            conv_order_ready,
            "demo-msg-ali-in-1",
            AgentWorkflowState.WAITING_FOR_CONFIRMATION,
            "buy_product",
            {"color": "مشکی", "size": "L", "quantity": 1},
            {"color": "black", "size": "L", "quantity": 1},
            {
                "intent": 0.92,
                "product": 0.88,
                "variant": 0.91,
                "requires_preview": False,
                "requires_handoff": False,
                "risk_reasons": [],
            },
            False,
            "Resolved hoodie variant HD-BLK-L; awaiting customer confirmation.",
        ),
        (
            conv_handoff,
            "demo-msg-sara-in-1",
            AgentWorkflowState.HUMAN_HANDOFF,
            "buy_product",
            {"color": "XL", "quantity": 1},
            {"color": "xl", "quantity": 1},
            {
                "intent": 0.7,
                "product": 0.61,
                "variant": 0.42,
                "requires_preview": True,
                "requires_handoff": True,
                "risk_reasons": ["low_variant_confidence"],
            },
            True,
            "Variant XL not confidently resolved; routed to operator handoff.",
        ),
    ]
    for (
        conversation,
        message_key,
        next_state,
        intent,
        extracted,
        normalized,
        risk_score,
        handoff,
        summary,
    ) in specs:
        if (
            db.scalar(
                select(AgentDecisionTrace)
                .where(AgentDecisionTrace.conversation_id == conversation.id)
                .limit(1)
            )
            is not None
        ):
            continue
        message = db.scalar(select(Message).where(Message.instagram_message_id == message_key))
        if message is None:
            continue
        agent_run = AgentRun(
            conversation_id=conversation.id,
            input_message_id=message.id,
            model_name="demo-seed-agent",
            prompt_version="seed-v1",
            input_json={"message_text": message.text},
            output_json={
                "intent": intent,
                "confidence": {
                    "intent": float(risk_score.get("intent", 0.8)),
                    "product": float(risk_score.get("product", 0.75)),
                    "variant": float(risk_score.get("variant", 0.7)),
                },
            },
            status=AgentRunStatus.SUCCESS,
            is_simulation=False,
        )
        db.add(agent_run)
        db.flush()
        db.add(
            AgentDecisionTrace(
                conversation_id=conversation.id,
                message_id=message.id,
                agent_run_id=agent_run.id,
                intent=intent,
                extracted_slots=extracted,
                normalized_slots=normalized,
                product_candidates=[
                    {"product_id": str(hoodie.id), "title": hoodie.title, "score": 0.88}
                ],
                selected_product_id=hoodie.id,
                variant_resolution={
                    "variant_id": str(hoodie_variant.id) if hoodie_variant is not None else None,
                    "sku": hoodie_variant.sku if hoodie_variant is not None else None,
                    "confidence": risk_score.get("variant", 0.5),
                },
                inventory_result={"available": hoodie_variant is not None},
                risk_score=risk_score,
                order_action={"order_id": None, "status": None},
                next_state=next_state.value,
                auto_send_allowed=not handoff,
                human_handoff_required=handoff,
                reasoning_summary=summary,
            )
        )
        db.add(
            AgentAction(
                conversation_id=conversation.id,
                action_name=intent,
                input_json={"message_id": str(message.id), "extracted_slots": extracted},
                output_json={
                    "normalized_slots": normalized,
                    "next_state": next_state.value,
                    "human_handoff_required": handoff,
                },
                confidence=float(risk_score.get("variant") or risk_score.get("intent") or 0.5),
                status=AgentActionStatus.SUCCESS,
            )
        )
    logger.info("Seeded agent decision traces for risk and conversation detail views")


def _pending_payment_for_order(
    db: Session, order_id: UUID, provider_reference: str
) -> Payment | None:
    for pending in db.new:
        if isinstance(pending, Payment) and (
            pending.order_id == order_id
            or pending.provider_reference == provider_reference
        ):
            return pending
    return None


def _pending_shipment_for_order(db: Session, order_id: UUID) -> Shipment | None:
    for pending in db.new:
        if isinstance(pending, Shipment) and pending.order_id == order_id:
            return pending
    return None


def _ensure_order_fulfillment_records(
    db: Session,
    order: Order,
    *,
    payment_status: OrderPaymentStatus,
    shipping_status: OrderShippingStatus,
    reference_key: str,
    order_status: OrderStatus | None = None,
) -> None:
    """Backfill Payment and Shipment rows so order detail pages show fulfillment info."""
    now = datetime.now(UTC)
    resolved_status = order_status or order.status
    provider_reference = f"demo-pay-{reference_key}"

    existing_payment = _pending_payment_for_order(db, order.id, provider_reference)
    if existing_payment is None:
        existing_payment = db.scalar(
            select(Payment).where(
                (Payment.order_id == order.id)
                | (Payment.provider_reference == provider_reference)
            ).limit(1)
        )

    if existing_payment is None:
        record_status: PaymentRecordStatus | None = None
        if payment_status == OrderPaymentStatus.PAID:
            record_status = PaymentRecordStatus.PAID
        elif payment_status == OrderPaymentStatus.PENDING:
            record_status = PaymentRecordStatus.PENDING
        elif resolved_status == OrderStatus.EXPIRED:
            record_status = PaymentRecordStatus.CANCELLED
        elif (
            payment_status == OrderPaymentStatus.UNPAID
            and resolved_status == OrderStatus.READY_FOR_CONFIRMATION
        ):
            record_status = PaymentRecordStatus.CREATED

        if record_status is not None:
            db.add(
                Payment(
                    order_id=order.id,
                    provider=PaymentProvider.MOCK,
                    status=record_status,
                    payment_url=f"http://localhost:8800/api/v1/payments/mock/pay/demo-{reference_key}",
                    provider_reference=provider_reference,
                    callback_processed_at=now - timedelta(hours=2)
                    if record_status == PaymentRecordStatus.PAID
                    else None,
                    raw_payload={"seed": True, "reference_key": reference_key},
                )
            )

    if shipping_status in {
        OrderShippingStatus.PREPARING,
        OrderShippingStatus.SHIPPED,
        OrderShippingStatus.DELIVERED,
    }:
        existing_shipment = _pending_shipment_for_order(db, order.id)
        if existing_shipment is None:
            existing_shipment = db.scalar(
                select(Shipment).where(Shipment.order_id == order.id).limit(1)
            )
        if existing_shipment is None:
            shipment_status = ShipmentStatus.PREPARING
            if shipping_status == OrderShippingStatus.SHIPPED:
                shipment_status = ShipmentStatus.SHIPPED
            elif shipping_status == OrderShippingStatus.DELIVERED:
                shipment_status = ShipmentStatus.DELIVERED
            tracking_suffix = reference_key.replace("demo-order-", "").upper()[:8]
            db.add(
                Shipment(
                    order_id=order.id,
                    provider=ShipmentProvider.MANUAL,
                    status=shipment_status,
                    tracking_code=(
                        f"DEMO-{tracking_suffix}"
                        if shipment_status in {ShipmentStatus.SHIPPED, ShipmentStatus.DELIVERED}
                        else None
                    ),
                    tracking_url=(
                        f"https://tracking.example.com/{tracking_suffix.lower()}"
                        if shipment_status in {ShipmentStatus.SHIPPED, ShipmentStatus.DELIVERED}
                        else None
                    ),
                    shipped_at=now - timedelta(hours=1)
                    if shipment_status != ShipmentStatus.PREPARING
                    else None,
                    delivered_at=now - timedelta(minutes=30)
                    if shipment_status == ShipmentStatus.DELIVERED
                    else None,
                )
            )


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
    recovery_status: OrderRecoveryStatus = OrderRecoveryStatus.NONE,
) -> Order:
    existing = db.scalar(
        select(Order).where(
            Order.shop_id == shop_id,
            Order.notes == reference_key,
        )
    )
    if existing is not None:
        if existing.recovery_status != recovery_status:
            existing.recovery_status = recovery_status
        _ensure_order_fulfillment_records(
            db,
            existing,
            payment_status=payment_status,
            shipping_status=shipping_status,
            reference_key=reference_key,
        )
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
        recovery_status=recovery_status,
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
    _ensure_order_fulfillment_records(
        db,
        order,
        payment_status=payment_status,
        shipping_status=shipping_status,
        reference_key=reference_key,
    )
    return order


def _backfill_demo_order_fulfillment(db: Session, shop_id: UUID) -> None:
    """Ensure payment/shipment rows exist for every order in the shop (idempotent)."""
    now = datetime.now(UTC)
    orders = db.scalars(select(Order).where(Order.shop_id == shop_id)).all()
    for order in orders:
        reference_key = order.notes or f"order-{str(order.id)[:8]}"
        _ensure_order_fulfillment_records(
            db,
            order,
            payment_status=order.payment_status,
            shipping_status=order.shipping_status,
            reference_key=reference_key,
            order_status=order.status,
        )

        # Showcase a fully shipped order in the demo UI.
        if reference_key == "demo-order-paid-hoodie":
            order.status = OrderStatus.ORDER_CREATED
            order.shipping_status = OrderShippingStatus.SHIPPED
            shipment = db.scalar(select(Shipment).where(Shipment.order_id == order.id).limit(1))
            if shipment is None:
                _ensure_order_fulfillment_records(
                    db,
                    order,
                    payment_status=order.payment_status,
                    shipping_status=OrderShippingStatus.SHIPPED,
                    reference_key=reference_key,
                    order_status=order.status,
                )
                shipment = db.scalar(select(Shipment).where(Shipment.order_id == order.id).limit(1))
            if shipment is not None:
                shipment.status = ShipmentStatus.SHIPPED
                shipment.tracking_code = "DEMO-HOODIE-TRK"
                shipment.tracking_url = "https://tracking.example.com/hoodie"
                shipment.shipped_at = now - timedelta(hours=1)

    logger.info("Backfilled payment and shipment records for %s demo orders", len(orders))


def _seed_channel_accounts(
    db: Session, *, shop: Shop, account: InstagramAccount, now: datetime
) -> None:
    """Create realistic connected social channels so channel setup and simulator UIs are populated."""
    specs = [
        {
            "provider": ChannelProvider.INSTAGRAM,
            "display_name": "بوت اینستاگرام مزون تهران",
            "external_account_id": account.ig_user_id,
            "webhook_url": "https://api.example.ir/webhooks/instagram/demo-shop",
            "status": ChannelAccountStatus.WEBHOOK_CONFIGURED,
            "capabilities_json": {
                "dm": True,
                "comments": True,
                "story_replies": True,
                "media_context": True,
            },
            "settings_json": {
                "legacy_instagram_account_id": str(account.id),
                "locale": "fa-IR",
                "timezone": "Asia/Tehran",
            },
        },
        {
            "provider": ChannelProvider.TELEGRAM,
            "display_name": "پشتیبانی تلگرام مزون تهران",
            "external_account_id": "telegram-demo-shop",
            "bot_username": "demo_shop_support_bot",
            "bot_id": "729000111",
            "webhook_url": "https://api.example.ir/webhooks/telegram/demo-shop",
            "status": ChannelAccountStatus.CONNECTED,
            "capabilities_json": {"dm": True, "attachments": True, "quick_replies": True},
            "settings_json": {"locale": "fa-IR", "handoff_queue": "tehran-support"},
        },
        {
            "provider": ChannelProvider.WHATSAPP,
            "display_name": "واتساپ فروش تهران",
            "external_account_id": "982100011122",
            "phone_number_id": "wa-demo-982100011122",
            "webhook_url": "https://api.example.ir/webhooks/whatsapp/demo-shop",
            "status": ChannelAccountStatus.CONNECTED,
            "capabilities_json": {"dm": True, "templates": True, "payments": False},
            "settings_json": {"locale": "fa-IR", "business_hours": "10:00-22:00"},
        },
    ]
    for spec in specs:
        channel = db.scalar(
            select(ChannelAccount).where(
                ChannelAccount.shop_id == shop.id,
                ChannelAccount.provider == spec["provider"],
                ChannelAccount.external_account_id == spec["external_account_id"],
            )
        )
        if channel is None:
            channel = ChannelAccount(
                shop_id=shop.id, last_validation_at=now - timedelta(minutes=30), **spec
            )
            db.add(channel)
        else:
            for key, value in spec.items():
                setattr(channel, key, value)
            channel.last_validation_at = now - timedelta(minutes=30)


def _seed_customer_preferences(db: Session, customers: list[Customer]) -> None:
    specs = {
        "demo-cust-ali": {
            "preferred_size": "L",
            "preferred_colors": ["black", "navy"],
            "preferred_categories": ["hoodie", "streetwear"],
        },
        "demo-cust-sara": {
            "preferred_size": "M",
            "preferred_colors": ["cream", "red"],
            "preferred_categories": ["dress", "outerwear"],
        },
        "demo-cust-reza": {
            "preferred_size": "L",
            "preferred_colors": ["black"],
            "preferred_categories": ["shirts"],
        },
        "demo-cust-nadia": {
            "preferred_size": "S",
            "preferred_colors": ["red", "white"],
            "preferred_categories": ["linen", "dress"],
        },
    }
    for customer in customers:
        data = specs.get(customer.instagram_user_id)
        if data is None:
            continue
        prefs = db.scalar(
            select(CustomerPreferences).where(CustomerPreferences.customer_id == customer.id)
        )
        if prefs is None:
            prefs = CustomerPreferences(customer_id=customer.id)
            db.add(prefs)
        prefs.preferred_size = data["preferred_size"]
        prefs.preferred_colors = data["preferred_colors"]
        prefs.preferred_categories = data["preferred_categories"]
        prefs.last_successful_size = data["preferred_size"]
        prefs.last_successful_city = customer.city or "Tehran"
        prefs.metadata_json = {"seed": True, "persona": customer.full_name, "market": "Iran"}


def _seed_catalog_copilot_data(
    db: Session, *, shop: Shop, products: list[Product], now: datetime
) -> None:
    for product in products:
        normalized = db.scalar(
            select(ProductNormalized).where(ProductNormalized.product_id == product.id)
        )
        if normalized is None:
            normalized = ProductNormalized(
                shop_id=shop.id,
                product_id=product.id,
                normalized_title=product.title.lower(),
                brand="Tehran Atelier",
                color=None,
                size=None,
                material="cotton"
                if "Hoodie" in product.title or "Shirt" in product.title
                else "linen",
                gender="unisex"
                if "Hoodie" in product.title or "Shirt" in product.title
                else "women",
                collection="Nowruz drop 1405",
                synonym_candidates=[
                    product.title,
                    f"خرید {product.title}",
                    f"{product.title} تهران",
                ],
                embedding_model="seed-demo-vector-v1",
                dense_vector_dim=1536,
                last_normalized_at=now - timedelta(hours=4),
                last_indexed_at=now - timedelta(hours=3),
            )
            db.add(normalized)
            db.flush()
        aliases = [product.title, f"{product.title} اصل", f"{product.title} مزون تهران"]
        if "Hoodie" in product.title:
            aliases.extend(["هودی مشکی", "هودی لش"])
        if "Dress" in product.title:
            aliases.extend(["پیراهن لینن", "لباس تابستانی قرمز"])
        for alias in aliases:
            if (
                db.scalar(
                    select(ProductAlias).where(
                        ProductAlias.shop_id == shop.id, ProductAlias.alias_text == alias
                    )
                )
                is None
            ):
                db.add(
                    ProductAlias(
                        shop_id=shop.id,
                        product_id=product.id,
                        normalized_product_id=normalized.id,
                        alias_text=alias,
                        language="fa" if any("\u0600" <= ch <= "\u06ff" for ch in alias) else "en",
                        source=CatalogAliasSource.GENERATED,
                        confidence=Decimal("0.9400"),
                    )
                )
        for variant in product.variants:
            label = " / ".join(part for part in [variant.color, variant.size] if part)
            for alias, alias_type in [
                (variant.sku, VariantAliasType.SKU),
                (label, VariantAliasType.COMBINED),
                (variant.color or "", VariantAliasType.COLOR),
                (variant.size or "", VariantAliasType.SIZE),
            ]:
                if (
                    alias
                    and db.scalar(
                        select(VariantAlias).where(
                            VariantAlias.shop_id == shop.id,
                            VariantAlias.variant_id == variant.id,
                            VariantAlias.alias_text == alias,
                        )
                    )
                    is None
                ):
                    db.add(
                        VariantAlias(
                            shop_id=shop.id,
                            variant_id=variant.id,
                            alias_text=alias,
                            alias_type=alias_type,
                            language="und",
                            source=CatalogAliasSource.GENERATED,
                        )
                    )
    if (
        db.scalar(select(CatalogImportJob).where(CatalogImportJob.shop_id == shop.id).limit(1))
        is None
    ):
        db.add(
            CatalogImportJob(
                shop_id=shop.id,
                status=CatalogImportJobStatus.COMPLETED,
                source_format="instagram+csv",
                total_rows=48,
                processed_rows=46,
                failed_rows=2,
                checkpoint={"last_file": "tehran_catalog_1405.csv"},
                started_at=now - timedelta(hours=5),
                completed_at=now - timedelta(hours=4),
                created_by_user_id=None,
            )
        )


def _seed_trust_and_scenario_data(
    db: Session,
    *,
    shop: Shop,
    admin: User,
    now: datetime,
    conv_handoff: Conversation,
    conv_order_ready: Conversation,
) -> None:
    policy = db.scalar(
        select(PolicyVersion).where(
            PolicyVersion.shop_id == shop.id, PolicyVersion.version == "seed-fa-ir-v1"
        )
    )
    if policy is None:
        policy = PolicyVersion(
            shop_id=shop.id,
            version="seed-fa-ir-v1",
            name="Iran pilot safety policy",
            is_active=True,
            created_by_user_id=admin.id,
            config_json={
                "max_auto_order_value": 7000000,
                "currency": "IRR",
                "require_handoff_for": [
                    "address_change_after_payment",
                    "low_confidence_variant",
                    "payment_dispute",
                ],
                "quiet_hours": {"timezone": "Asia/Tehran", "from": "23:00", "to": "09:00"},
            },
        )
        db.add(policy)
        db.flush()
    scenarios = [
        {
            "item_key": "fa_buy_exact_variant",
            "message_text": "سلام همین هودی مشکی سایز L رو می‌خوام، تهران هستم",
            "shared_post_url": POST_URL_HOODIE,
            "instagram_user_id": "demo-cust-ali",
            "expected_json": {
                "intent": "buy_product",
                "product": HOODIE_TITLE,
                "variant": "HD-BLK-L",
                "handoff": False,
            },
        },
        {
            "item_key": "fa_out_of_stock",
            "message_text": "پیراهن قرمز سایز M موجوده؟",
            "shared_post_url": POST_URL_DRESS,
            "instagram_user_id": "demo-cust-sara",
            "expected_json": {
                "intent": "availability_check",
                "reason": "out_of_stock",
                "handoff": False,
            },
        },
        {
            "item_key": "fa_payment_dispute",
            "message_text": "پرداخت کردم ولی لینک هنوز میگه پرداخت نشده",
            "instagram_user_id": "demo-cust-nadia",
            "expected_json": {"intent": "payment_support", "handoff": True},
        },
    ]
    pack = db.scalar(
        select(ScenarioPack).where(
            ScenarioPack.shop_id == shop.id,
            ScenarioPack.name == "Golden Persian Instagram sales scenarios",
        )
    )
    if pack is None:
        db.add(
            ScenarioPack(
                shop_id=shop.id,
                name="Golden Persian Instagram sales scenarios",
                pack_type=ScenarioPackType.HANDCRAFTED,
                description="واقع‌گرایانه‌ترین سناریوهای فروش اینستاگرامی برای بازار ایران.",
                scenarios_json=scenarios,
                is_golden=True,
                created_by_user_id=admin.id,
            )
        )
    if (
        db.scalar(
            select(SimulatorRun).where(
                SimulatorRun.shop_id == shop.id,
                SimulatorRun.label == "Seeded golden replay - Iran storefront",
            )
        )
        is None
    ):
        run = SimulatorRun(
            shop_id=shop.id,
            created_by_user_id=admin.id,
            label="Seeded golden replay - Iran storefront",
            source_type=SimulatorRunSourceType.SCENARIO_PACK,
            model_version="seed-agent-v1",
            prompt_version="fa-ir-sales-v1",
            policy_version_id=policy.id,
            catalog_snapshot_hash="seed-catalog-fa-ir-001",
            catalog_snapshot_json={
                "products": [HOODIE_TITLE, DRESS_TITLE, "Demo Black Shirt"],
                "currency": "IRR",
            },
            status=SimulatorRunStatus.COMPLETED,
            total_items=3,
            passed_items=2,
            failed_items=1,
            diff_summary_json={
                "passed_rate": 0.667,
                "known_gap": "payment dispute requires operator verification",
            },
            started_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=1, minutes=58),
        )
        db.add(run)
        db.flush()
        for item in scenarios:
            passed = item["item_key"] != "fa_payment_dispute"
            db.add(
                SimulatorRunItem(
                    run_id=run.id,
                    item_key=item["item_key"],
                    input_json=item,
                    expected_json=item["expected_json"],
                    actual_json={
                        **item["expected_json"],
                        "handoff": item["expected_json"].get("handoff", False),
                    },
                    diff_json={
                        "passed": passed,
                        "mismatches": [] if passed else ["operator_payment_verification_required"],
                    },
                    passed=passed,
                    conversation_id=conv_handoff.id if not passed else conv_order_ready.id,
                    processing_time_ms=420 if passed else 880,
                )
            )
    if (
        db.scalar(
            select(Incident).where(
                Incident.shop_id == shop.id,
                Incident.title == "Payment callback mismatch during Instagram sale",
            )
        )
        is None
    ):
        incident = Incident(
            shop_id=shop.id,
            title="Payment callback mismatch during Instagram sale",
            severity=IncidentSeverity.MEDIUM,
            status=IncidentStatus.MITIGATED,
            trigger=IncidentTrigger.POLICY_BREACH,
            opened_by_user_id=admin.id,
            opened_at=now - timedelta(hours=3),
            resolved_at=now - timedelta(hours=2, minutes=20),
            summary_json={
                "affected_orders": 1,
                "market": "Iran",
                "mitigation": "payments require human verification until gateway callback recovers",
            },
        )
        db.add(incident)
        db.flush()
        db.add(
            IncidentEvent(
                incident_id=incident.id,
                event_type="opened",
                actor_user_id=admin.id,
                description="زرین‌پال callback با وضعیت سفارش همخوان نبود؛ auto-send متوقف شد.",
                metadata_json={"gateway": "zarinpal-demo"},
                affected_conversation_ids=[str(conv_handoff.id)],
                created_at=now - timedelta(hours=3),
            )
        )
        db.add(
            IncidentEvent(
                incident_id=incident.id,
                event_type="mitigated",
                actor_user_id=admin.id,
                description="Rule switched payment disputes to human handoff.",
                metadata_json={"policy_version": policy.version},
                affected_conversation_ids=[str(conv_handoff.id)],
                created_at=now - timedelta(hours=2, minutes=20),
            )
        )


def _seed_social_admin_data(
    db: Session, *, shop: Shop, admin: User, conv_handoff: Conversation
) -> None:
    if (
        db.scalar(
            select(AdminTask)
            .where(AdminTask.shop_id == shop.id, AdminTask.task_type == "campaign_brief")
            .limit(1)
        )
        is None
    ):
        db.add(
            AdminTask(
                shop_id=shop.id,
                requested_by_user_id=admin.id,
                task_type="campaign_brief",
                input_json={"campaign": "Nowruz drop", "channel": "instagram"},
                output_json={
                    "draft_caption": "کالکشن نوروزی آماده سفارش در دایرکت است ✨",
                    "dm_prompt": "برای قیمت کلمه قیمت رو کامنت کن",
                },
                status="pending",
                requires_approval=True,
            )
        )
    message = db.scalar(select(Message).where(Message.instagram_message_id == "demo-msg-sara-in-1"))
    if (
        message is not None
        and db.scalar(
            select(OperatorCorrection)
            .where(
                OperatorCorrection.shop_id == shop.id,
                OperatorCorrection.conversation_id == conv_handoff.id,
            )
            .limit(1)
        )
        is None
    ):
        correction = OperatorCorrection(
            shop_id=shop.id,
            conversation_id=conv_handoff.id,
            message_id=message.id,
            correction_type="variant_alias",
            before_json={"raw": "XL", "normalized": None},
            after_json={"raw": "XL", "normalized": "extra_large", "handoff": True},
            operator_id=admin.id,
        )
        db.add(correction)
        db.flush()
        db.add(
            AutomationRuleSuggestion(
                shop_id=shop.id,
                source_correction_id=correction.id,
                suggested_rule_json={
                    "rule": "map_size_alias",
                    "raw_values": ["XL", "ایکس لارج"],
                    "normalized": "XL",
                    "requires_inventory_check": True,
                },
                status="pending",
            )
        )


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
                risk_policy_json={
                    "handoff_for_high_risk": True,
                    "handoff_for_low_variant_confidence": True,
                },
            )
        )
        logger.info("Created shop agent studio settings")
    elif agent_settings is not None and not agent_settings.risk_policy_json:
        agent_settings.risk_policy_json = {
            "handoff_for_high_risk": True,
            "handoff_for_low_variant_confidence": True,
        }

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
        if (
            db.scalar(
                select(ColorAlias).where(
                    ColorAlias.shop_id == shop.id,
                    ColorAlias.raw_value == alias[0],
                    ColorAlias.language == "und",
                )
            )
            is None
        ):
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
        if (
            db.scalar(
                select(InstagramProductMap).where(
                    InstagramProductMap.shop_id == shop.id,
                    InstagramProductMap.instagram_post_url == post_url,
                )
            )
            is None
        ):
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
        (
            "price",
            TriggerSourceType.COMMENT,
            "Thanks! I sent you pricing in DM. Which color and size?",
        ),
        (
            "order",
            TriggerSourceType.DIRECT_DM,
            "Happy to help with your order — tell me color and size.",
        ),
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
        select(ProductVariant).where(
            ProductVariant.product_id == hoodie.id, ProductVariant.sku == "HD-BLK-L"
        )
    )
    dress_variant = db.scalar(
        select(ProductVariant).where(
            ProductVariant.product_id == dress.id, ProductVariant.sku == "DR-RED-S"
        )
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
        db,
        shop.id,
        instagram_user_id="demo-cust-sara",
        full_name="Sara Karimi",
        phone="09129876543",
    )
    reza = _get_or_create_customer(
        db,
        shop.id,
        instagram_user_id="demo-cust-reza",
        full_name="Reza Ahmadi",
        phone="09121112222",
    )
    nadia = _get_or_create_customer(
        db,
        shop.id,
        instagram_user_id="demo-cust-nadia",
        full_name="Nadia Hosseini",
        phone="09123334444",
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

    if (
        db.scalar(
            select(ConversationSlots).where(
                ConversationSlots.conversation_id == conv_order_ready.id
            )
        )
        is None
        and hoodie_variant is not None
    ):
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

    if (
        db.scalar(
            select(ConversationSlots).where(ConversationSlots.conversation_id == conv_handoff.id)
        )
        is None
    ):
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
            status=OrderStatus.PAYMENT_PENDING,
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
                status=OrderStatus.READY_FOR_CONFIRMATION,
                payment_status=OrderPaymentStatus.UNPAID,
                shipping_status=OrderShippingStatus.NOT_STARTED,
                customer_name="Reza Ahmadi",
                reference_key="demo-order-draft-shirt",
            )

        if (
            db.scalar(
                select(SuggestedReply).where(
                    SuggestedReply.conversation_id == conv_handoff.id,
                    SuggestedReply.suggested_text.like("I can check%"),
                )
            )
            is None
        ):
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
        if (
            db.scalar(
                select(TriggerEvent).where(TriggerEvent.trigger_id == price_trigger.id).limit(1)
            )
            is None
        ):
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

    if (
        db.scalar(
            select(UnavailableDemandLog)
            .where(
                UnavailableDemandLog.shop_id == shop.id,
                UnavailableDemandLog.reason == "out_of_stock",
            )
            .limit(1)
        )
        is None
    ):
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

    _seed_conversation_events(
        db,
        now=now,
        admin=admin,
        conv_order_ready=conv_order_ready,
        conv_handoff=conv_handoff,
        conv_sim=conv_sim,
        hoodie=hoodie,
        hoodie_variant=hoodie_variant,
    )

    _seed_dashboard_metrics_demo(
        db,
        shop=shop,
        account=account,
        now=now,
        hoodie=hoodie,
        dress=dress,
        black_shirt=black_shirt,
        hoodie_variant=hoodie_variant,
        dress_variant=dress_variant,
        shirt_variant=shirt_variant,
        ali=ali,
        sara=sara,
        reza=reza,
        conv_order_ready=conv_order_ready,
        conv_handoff=conv_handoff,
        conv_sim=conv_sim,
    )

    _seed_dress_inquiry_events(
        db,
        now=now,
        dress=dress,
        dress_variant=dress_variant,
    )

    _seed_failed_jobs(
        db,
        shop=shop,
        account=account,
        conv_order_ready=conv_order_ready,
        conv_handoff=conv_handoff,
        ali=ali,
        sara=sara,
    )

    _seed_channel_accounts(db, shop=shop, account=account, now=now)
    _seed_customer_preferences(db, [ali, sara, reza, nadia])
    _seed_catalog_copilot_data(
        db,
        shop=shop,
        products=[product for product in [black_shirt, hoodie, dress] if product is not None],
        now=now,
    )
    _seed_trust_and_scenario_data(
        db,
        shop=shop,
        admin=admin,
        now=now,
        conv_handoff=conv_handoff,
        conv_order_ready=conv_order_ready,
    )
    _seed_social_admin_data(db, shop=shop, admin=admin, conv_handoff=conv_handoff)

    _seed_recovery_rule(db, shop.id)
    _seed_decision_traces(
        db,
        conv_order_ready=conv_order_ready,
        conv_handoff=conv_handoff,
        hoodie=hoodie,
        hoodie_variant=hoodie_variant,
    )

    _seed_dashboard_trends_history(
        db,
        shop=shop,
        account=account,
        now=now,
        hoodie=hoodie,
        hoodie_variant=hoodie_variant,
        reza=reza,
    )

    _backfill_demo_order_fulfillment(db, shop.id)

    _seed_agent_run_failures(
        db,
        conv_handoff=conv_handoff,
        conv_sim=conv_sim,
        now=now,
    )

    _seed_analytics_signals(
        db,
        shop=shop,
        now=now,
        conv_order_ready=conv_order_ready,
        conv_handoff=conv_handoff,
    )

    db.flush()
    logger.info("Rich demo data seeded for shop %s", shop.slug)


def main() -> None:
    """Entry point for `python -m app.scripts.seed_demo_data`."""
    from app.scripts.seed import seed

    seed()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
