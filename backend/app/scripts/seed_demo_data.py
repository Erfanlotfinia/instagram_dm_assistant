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
    AgentRunStatus,
    AgentWorkflowState,
    ConfidenceSource,
    ConversationPriorityLevel,
    ConversationState,
    FailedJobStatus,
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
    ShipmentProvider,
    ShipmentStatus,
    SellingStyle,
    SuggestedReplyGeneratedBy,
    SuggestedReplyStatus,
    TriggerSourceType,
    UpsellSuggestionStatus,
    UserRole,
)
from app.domain.models import (
    AbandonedOrderRecoveryRule,
    AgentDecisionTrace,
    AgentRun,
    ColorAlias,
    CommentToDmTrigger,
    Conversation,
    ConversationSlots,
    Customer,
    FailedJob,
    InstagramAccount,
    InstagramProductMap,
    Message,
    Order,
    OrderItem,
    Payment,
    Product,
    Shipment,
    ProductUpsell,
    ProductVariant,
    Shop,
    ShopAgentSettings,
    ShopMember,
    SizeAlias,
    SuggestedReply,
    TriggerEvent,
    UnavailableDemandLog,
    UpsellSuggestion,
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
    if db.scalar(
        select(Order).where(
            Order.shop_id == shop.id,
            Order.notes == "demo-order-recovered-hoodie",
        )
    ) is not None:
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
        ("demo-msg-ali-in-2", conv_order_ready.id, "آدرس همینه که قبلاً فرستادم", now - timedelta(minutes=15)),
        ("demo-msg-sara-in-2", conv_handoff.id, "What colors do you have?", now - timedelta(minutes=5)),
        ("demo-msg-sara-in-3", conv_handoff.id, "Maybe navy instead?", now - timedelta(minutes=3)),
        ("demo-msg-reza-in-2", conv_sim.id, "قیمت چنده؟", now - timedelta(hours=1, minutes=50)),
        ("demo-msg-nadia-in-1", conv_dress.id, "Is the red dress available in S?", now - timedelta(hours=6)),
        ("demo-msg-nadia-in-2", conv_dress.id, "Perfect, I'll take it", now - timedelta(hours=5, minutes=45)),
    ]:
        _ensure_message(
            db,
            conversation_id=conversation_id,
            instagram_message_id=message_id,
            direction=MessageDirection.INBOUND,
            text=text,
            created_at=created_at,
        )

    if db.scalar(select(ConversationSlots).where(ConversationSlots.conversation_id == conv_dress.id)) is None:
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

    if black_shirt is not None and db.scalar(
        select(ConversationSlots).where(ConversationSlots.conversation_id == conv_sim.id)
    ) is None:
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
        (conv_handoff.id, sara.id, UpsellSuggestionStatus.SUGGESTED, "demo-upsell-suggested-handoff"),
        (conv_sim.id, reza.id, UpsellSuggestionStatus.SUGGESTED, "demo-upsell-suggested-sim"),
        (conv_dress.id, nadia.id, UpsellSuggestionStatus.SUGGESTED, "demo-upsell-suggested-dress"),
    ]
    for conversation_id, customer_id, status, marker in upsell_specs:
        if db.scalar(
            select(UpsellSuggestion).where(
                UpsellSuggestion.shop_id == shop.id,
                UpsellSuggestion.suggested_text.like(f"%{marker}%"),
            )
        ) is not None:
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
    if db.scalar(select(FailedJob).where(FailedJob.error_message.like("demo:%")).limit(1)) is not None:
        return

    inbound_order = db.scalar(
        select(Message).where(Message.instagram_message_id == "demo-msg-ali-in-1")
    )
    inbound_handoff = db.scalar(
        select(Message).where(Message.instagram_message_id == "demo-msg-sara-in-1")
    )
    now = datetime.now(UTC)
    settings_queue = "instagram.message.received"
    dlq_queue = "instagram.message.received.dlq"

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
            traceback='ValidationError: 3 validation errors for MessageReceivedJob\nmessage_id\n  field required',
            retry_count=3,
            max_retries=3,
            status=FailedJobStatus.FAILED,
            resolved=False,
            created_at=now - timedelta(minutes=2),
        )
    )
    logger.info("Seeded demo failed jobs for system health UI")


def _seed_recovery_rule(db: Session, shop_id: UUID) -> None:
    if db.scalar(
        select(AbandonedOrderRecoveryRule).where(AbandonedOrderRecoveryRule.shop_id == shop_id).limit(1)
    ) is not None:
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
    if db.scalar(select(AgentDecisionTrace).limit(1)) is not None:
        return

    specs = [
        (
            conv_order_ready,
            "demo-msg-ali-in-1",
            AgentWorkflowState.WAITING_FOR_CONFIRMATION,
            "buy_product",
            {"color": "مشکی", "size": "L", "quantity": 1},
            {"color": "black", "size": "L", "quantity": 1},
            {"intent": 0.92, "variant": 0.91, "requires_preview": False, "requires_handoff": False, "risk_reasons": []},
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
            {"intent": 0.7, "variant": 0.42, "requires_preview": True, "requires_handoff": True, "risk_reasons": ["low_variant_confidence"]},
            True,
            "Variant XL not confidently resolved; routed to operator handoff.",
        ),
    ]
    for conversation, message_key, next_state, intent, extracted, normalized, risk_score, handoff, summary in specs:
        message = db.scalar(select(Message).where(Message.instagram_message_id == message_key))
        if message is None:
            continue
        agent_run = AgentRun(
            conversation_id=conversation.id,
            input_message_id=message.id,
            model_name="demo-seed-agent",
            prompt_version="seed-v1",
            input_json={"message_text": message.text},
            output_json={"intent": intent},
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
                product_candidates=[{"product_id": str(hoodie.id), "title": hoodie.title, "score": 0.88}],
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
    logger.info("Seeded agent decision traces for risk and conversation detail views")


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

    if db.scalar(select(Payment).where(Payment.order_id == order.id).limit(1)) is None:
        record_status: PaymentRecordStatus | None = None
        if payment_status == OrderPaymentStatus.PAID:
            record_status = PaymentRecordStatus.PAID
        elif payment_status == OrderPaymentStatus.PENDING:
            record_status = PaymentRecordStatus.PENDING
        elif resolved_status == OrderStatus.EXPIRED:
            record_status = PaymentRecordStatus.CANCELLED
        elif (
            payment_status == OrderPaymentStatus.UNPAID
            and resolved_status == OrderStatus.WAITING_FOR_CONFIRMATION
        ):
            record_status = PaymentRecordStatus.CREATED

        if record_status is not None:
            db.add(
                Payment(
                    order_id=order.id,
                    provider=PaymentProvider.MOCK,
                    status=record_status,
                    payment_url=f"http://localhost:8800/api/v1/payments/mock/pay/demo-{reference_key}",
                    provider_reference=f"demo-pay-{reference_key}",
                    callback_processed_at=now - timedelta(hours=2) if record_status == PaymentRecordStatus.PAID else None,
                    raw_payload={"seed": True, "reference_key": reference_key},
                )
            )

    if shipping_status in {
        OrderShippingStatus.PREPARING,
        OrderShippingStatus.SHIPPED,
        OrderShippingStatus.DELIVERED,
    }:
        if db.scalar(select(Shipment).where(Shipment.order_id == order.id).limit(1)) is None:
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
                    shipped_at=now - timedelta(hours=1) if shipment_status != ShipmentStatus.PREPARING else None,
                    delivered_at=now - timedelta(minutes=30) if shipment_status == ShipmentStatus.DELIVERED else None,
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
            order.status = OrderStatus.SHIPPED
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
    dress_variant = db.scalar(
        select(ProductVariant).where(ProductVariant.product_id == dress.id, ProductVariant.sku == "DR-RED-S")
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

    _seed_failed_jobs(
        db,
        shop=shop,
        account=account,
        conv_order_ready=conv_order_ready,
        conv_handoff=conv_handoff,
        ali=ali,
        sara=sara,
    )

    _seed_recovery_rule(db, shop.id)
    _seed_decision_traces(
        db,
        conv_order_ready=conv_order_ready,
        conv_handoff=conv_handoff,
        hoodie=hoodie,
        hoodie_variant=hoodie_variant,
    )

    _backfill_demo_order_fulfillment(db, shop.id)

    db.flush()
    logger.info("Rich demo data seeded for shop %s", shop.slug)


def main() -> None:
    """Entry point for `python -m app.scripts.seed_demo_data`."""
    from app.scripts.seed import seed

    seed()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
