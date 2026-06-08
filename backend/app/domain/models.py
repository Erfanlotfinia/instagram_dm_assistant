from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import (
    AgentActionStatus,
    AgentMode,
    AgentRunStatus,
    AgentWorkflowState,
    ConfidenceSource,
    ConversationState,
    InstagramAccountStatus,
    InventoryMovementType,
    MessageChannel,
    MessageDirection,
    MessageType,
    OrderPaymentStatus,
    OrderShippingStatus,
    OrderStatus,
    PaymentProvider,
    PaymentRecordStatus,
    ProductStatus,
    ShipmentProvider,
    ShipmentStatus,
    ShopStatus,
    SellingStyle,
    SuggestedReplyGeneratedBy,
    SuggestedReplyStatus,
    TriggerSourceType,
    UserRole,
    WebhookProcessingStatus,
    WebhookProvider,
)
from app.domain.mixins import TimestampMixin


def enum_values(enum_cls: type[Any]) -> list[str]:
    return [member.value for member in enum_cls]


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    shop_memberships: Mapped[list[ShopMember]] = relationship(back_populates="user")
    assigned_conversations: Mapped[list[Conversation]] = relationship(
        back_populates="assigned_operator",
        foreign_keys="Conversation.assigned_operator_id",
    )


class Shop(Base, TimestampMixin):
    __tablename__ = "shops"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[ShopStatus] = mapped_column(
        Enum(ShopStatus, name="shop_status"), nullable=False, default=ShopStatus.ACTIVE
    )
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    agent_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    onboarding_flags: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    members: Mapped[list[ShopMember]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    instagram_accounts: Mapped[list[InstagramAccount]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    customers: Mapped[list[Customer]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    products: Mapped[list[Product]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    instagram_product_maps: Mapped[list[InstagramProductMap]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    orders: Mapped[list[Order]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    trigger_rules: Mapped[list[CommentToDmTrigger]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    agent_studio_settings: Mapped[ShopAgentSettings | None] = relationship(back_populates="shop", cascade="all, delete-orphan", uselist=False)
    suggested_replies: Mapped[list[SuggestedReply]] = relationship(back_populates="shop", cascade="all, delete-orphan")


class ShopMember(Base):
    __tablename__ = "shop_members"
    __table_args__ = (UniqueConstraint("shop_id", "user_id", name="uq_shop_members_shop_user"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="shop_member_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    shop: Mapped[Shop] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="shop_memberships")


class InstagramAccount(Base, TimestampMixin):
    __tablename__ = "instagram_accounts"
    __table_args__ = (UniqueConstraint("shop_id", "ig_user_id", name="uq_instagram_accounts_shop_ig_user"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ig_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    webhook_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[InstagramAccountStatus] = mapped_column(
        Enum(InstagramAccountStatus, name="instagram_account_status"),
        nullable=False,
        default=InstagramAccountStatus.CONNECTED,
    )

    shop: Mapped[Shop] = relationship(back_populates="instagram_accounts")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="instagram_account")


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("shop_id", "instagram_user_id", name="uq_customers_shop_instagram_user"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instagram_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    shop: Mapped[Shop] = relationship(back_populates="customers")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="customer")
    orders: Mapped[list[Order]] = relationship(back_populates="customer")


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instagram_account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("instagram_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="instagram", index=True)
    channel_conversation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    channel_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    trigger_rule_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("comment_to_dm_triggers.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state: Mapped[ConversationState] = mapped_column(
        Enum(ConversationState, name="conversation_state"),
        nullable=False,
        default=ConversationState.OPEN,
    )
    last_intent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    assigned_operator_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    handoff_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    handoff_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    workflow_state: Mapped[AgentWorkflowState] = mapped_column(
        Enum(AgentWorkflowState, name="agent_workflow_state"),
        nullable=False,
        default=AgentWorkflowState.IDLE,
    )
    agent_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agent_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_simulation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    suggested_outbound: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    preview_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    shop: Mapped[Shop] = relationship(back_populates="conversations")
    instagram_account: Mapped[InstagramAccount] = relationship(back_populates="conversations")
    customer: Mapped[Customer] = relationship(back_populates="conversations")
    assigned_operator: Mapped[User | None] = relationship(
        back_populates="assigned_conversations",
        foreign_keys=[assigned_operator_id],
    )
    messages: Mapped[list[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    agent_actions: Mapped[list[AgentAction]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    agent_runs: Mapped[list[AgentRun]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    slots: Mapped[ConversationSlots | None] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        uselist=False,
    )
    orders: Mapped[list[Order]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    suggested_replies: Mapped[list[SuggestedReply]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class WebhookEvent(Base, TimestampMixin):
    __tablename__ = "webhook_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[WebhookProvider] = mapped_column(
        Enum(WebhookProvider, name="webhook_provider"), nullable=False
    )
    shop_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="SET NULL"), nullable=True, index=True
    )
    instagram_account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("instagram_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, default="instagram.messaging")
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    processing_status: Mapped[WebhookProcessingStatus] = mapped_column(
        Enum(WebhookProcessingStatus, name="webhook_processing_status"),
        nullable=False,
        default=WebhookProcessingStatus.RECEIVED,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("instagram_message_id", name="uq_messages_instagram_message_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction: Mapped[MessageDirection] = mapped_column(
        Enum(MessageDirection, name="message_direction"), nullable=False
    )
    channel: Mapped[MessageChannel] = mapped_column(
        Enum(MessageChannel, name="message_channel"), nullable=False, default=MessageChannel.INSTAGRAM
    )
    instagram_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    channel_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    raw_channel_payload_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("raw_channel_payloads.id", ondelete="SET NULL"), nullable=True, index=True)
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType, name="message_type"), nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class AgentAction(Base):
    __tablename__ = "agent_actions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_name: Mapped[str] = mapped_column(String(128), nullable=False)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    status: Mapped[AgentActionStatus] = mapped_column(
        Enum(AgentActionStatus, name="agent_action_status"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    conversation: Mapped[Conversation] = relationship(back_populates="agent_actions")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input_message_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(AgentRunStatus, name="agent_run_status"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    conversation: Mapped[Conversation] = relationship(back_populates="agent_runs")


class ConversationSlots(Base):
    __tablename__ = "conversation_slots"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    product_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_variant_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    instagram_post_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    color: Mapped[str | None] = mapped_column(String(64), nullable=True)
    normalized_color: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    normalized_size: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_candidates: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    variant_alternatives: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    missing_fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    conversation: Mapped[Conversation] = relationship(back_populates="slots")


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"), nullable=False, default=ProductStatus.ACTIVE
    )
    base_price: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    main_image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_chart: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    shop: Mapped[Shop] = relationship(back_populates="products")
    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    instagram_maps: Mapped[list[InstagramProductMap]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductVariant(Base, TimestampMixin):
    __tablename__ = "product_variants"
    __table_args__ = (UniqueConstraint("product_id", "sku", name="uq_product_variants_product_sku"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    color: Mapped[str | None] = mapped_column(String(64), nullable=True)
    normalized_color: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    normalized_size: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    price: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    product: Mapped[Product] = relationship(back_populates="variants")
    inventory_movements: Mapped[list[InventoryMovement]] = relationship(
        back_populates="product_variant", cascade="all, delete-orphan"
    )

    @property
    def available_stock(self) -> int:
        return self.stock_quantity - self.reserved_quantity


class InstagramProductMap(Base, TimestampMixin):
    __tablename__ = "instagram_product_maps"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instagram_account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("instagram_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    instagram_media_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    instagram_post_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    confidence_source: Mapped[ConfidenceSource] = mapped_column(
        Enum(ConfidenceSource, name="confidence_source"), nullable=False, default=ConfidenceSource.MANUAL
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    admin_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    visual_hint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    caption_hint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    shop: Mapped[Shop] = relationship(back_populates="instagram_product_maps")
    instagram_account: Mapped[InstagramAccount] = relationship()
    product: Mapped[Product] = relationship(back_populates="instagram_maps")


class RawChannelPayload(Base):
    __tablename__ = "raw_channel_payloads"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=True, index=True)
    provider: Mapped[MessageChannel] = mapped_column(Enum(MessageChannel, name="message_channel"), nullable=False, index=True)
    external_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class CommentToDmTrigger(Base, TimestampMixin):
    __tablename__ = "comment_to_dm_triggers"
    __table_args__ = (
        UniqueConstraint("shop_id", "instagram_account_id", "instagram_media_id", "source_type", "keyword", name="uq_comment_to_dm_trigger_keyword"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    instagram_account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("instagram_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    instagram_media_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_type: Mapped[TriggerSourceType] = mapped_column(Enum(TriggerSourceType, name="trigger_source_type"), nullable=False, default=TriggerSourceType.COMMENT, index=True)
    keyword: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    response_template: Mapped[str] = mapped_column(Text, nullable=False)
    target_product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    shop: Mapped[Shop] = relationship(back_populates="trigger_rules")
    instagram_account: Mapped[InstagramAccount] = relationship()
    target_product: Mapped[Product | None] = relationship()
    events: Mapped[list[TriggerEvent]] = relationship(back_populates="trigger", cascade="all, delete-orphan")


class TriggerEvent(Base):
    __tablename__ = "trigger_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    trigger_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("comment_to_dm_triggers.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    matched_keyword: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[TriggerSourceType] = mapped_column(Enum(TriggerSourceType, name="trigger_source_type"), nullable=False)
    dm_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paid_order_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    revenue_amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    trigger: Mapped[CommentToDmTrigger] = relationship(back_populates="events")


class ColorAlias(Base, TimestampMixin):
    __tablename__ = "color_aliases"
    __table_args__ = (UniqueConstraint("shop_id", "raw_value", "language", name="uq_color_alias_shop_raw_language"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=True, index=True)
    raw_value: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    normalized_value: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="und")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


class SizeAlias(Base, TimestampMixin):
    __tablename__ = "size_aliases"
    __table_args__ = (UniqueConstraint("shop_id", "raw_value", "category", name="uq_size_alias_shop_raw_category"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=True, index=True)
    raw_value: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    normalized_value: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


class ProductSizeChart(Base, TimestampMixin):
    __tablename__ = "product_size_charts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    chart_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class UnavailableDemand(Base):
    __tablename__ = "unavailable_demand"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    requested_color: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    requested_size: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    lost_revenue_estimate: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class UnavailableDemandLog(Base):
    __tablename__ = "unavailable_demand_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    requested_color_raw: Mapped[str | None] = mapped_column(String(128), nullable=True)
    requested_color_normalized: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    requested_size_raw: Mapped[str | None] = mapped_column(String(128), nullable=True)
    requested_size_normalized: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    requested_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reason: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    conversation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    estimated_lost_revenue: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    product_variant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    movement_type: Mapped[InventoryMovementType] = mapped_column(
        Enum(InventoryMovementType, name="inventory_movement_type"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    product_variant: Mapped[ProductVariant] = relationship(back_populates="inventory_movements")


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"), nullable=False, default=OrderStatus.DRAFT, index=True
    )
    subtotal_amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    shipping_amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    payment_status: Mapped[OrderPaymentStatus] = mapped_column(
        Enum(OrderPaymentStatus, name="order_payment_status"),
        nullable=False,
        default=OrderPaymentStatus.UNPAID,
        index=True,
    )
    shipping_status: Mapped[OrderShippingStatus] = mapped_column(
        Enum(OrderShippingStatus, name="order_shipping_status"),
        nullable=False,
        default=OrderShippingStatus.NOT_STARTED,
        index=True,
    )
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    city: Mapped[str] = mapped_column(String(128), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    postal_code: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    approval_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_callback_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    shop: Mapped[Shop] = relationship(back_populates="orders")
    customer: Mapped[Customer] = relationship(back_populates="orders")
    conversation: Mapped[Conversation] = relationship(back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    shipments: Mapped[list[Shipment]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_variant_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_title_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_color_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    variant_size_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sku_snapshot: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False)
    total_price: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, name="payment_provider"), nullable=False
    )
    status: Mapped[PaymentRecordStatus] = mapped_column(
        Enum(PaymentRecordStatus, name="payment_record_status"),
        nullable=False,
        default=PaymentRecordStatus.CREATED,
        index=True,
    )
    payment_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    callback_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order] = relationship(back_populates="payments")


class Shipment(Base, TimestampMixin):
    __tablename__ = "shipments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[ShipmentProvider] = mapped_column(
        Enum(ShipmentProvider, name="shipment_provider"), nullable=False, default=ShipmentProvider.MANUAL
    )
    status: Mapped[ShipmentStatus] = mapped_column(
        Enum(ShipmentStatus, name="shipment_status"),
        nullable=False,
        default=ShipmentStatus.PENDING,
        index=True,
    )
    tracking_code: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    tracking_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order] = relationship(back_populates="shipments")


class AgentDecisionTrace(Base):
    __tablename__ = "agent_decision_traces"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True)
    agent_run_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    intent: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    extracted_slots: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    product_candidates: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    selected_product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    variant_resolution: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    inventory_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    order_action: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    next_state: Mapped[str] = mapped_column(String(128), nullable=False)
    outbound_message_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True)
    auto_send_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    human_handoff_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reasoning_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class ShopAgentSettings(Base):
    __tablename__ = "shop_agent_settings"

    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), primary_key=True)
    auto_send_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    preview_required_for_low_confidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    preview_required_for_first_order: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    preview_required_for_high_value_order: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    confidence_threshold_intent: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=False, default=0.75)
    confidence_threshold_product: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=False, default=0.80)
    confidence_threshold_variant: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=False, default=0.85)
    confidence_threshold_address: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=False, default=0.80)
    high_value_order_threshold: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    brand_voice: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode: Mapped[AgentMode] = mapped_column(Enum(AgentMode, name="agent_mode"), nullable=False, default=AgentMode.COPILOT)
    selling_style: Mapped[SellingStyle] = mapped_column(Enum(SellingStyle, name="selling_style"), nullable=False, default=SellingStyle.FRIENDLY)
    discount_policy_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    handoff_policy_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    shop: Mapped[Shop] = relationship(back_populates="agent_studio_settings")


class SuggestedReply(Base):
    __tablename__ = "suggested_replies"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True)
    suggested_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SuggestedReplyStatus] = mapped_column(Enum(SuggestedReplyStatus, name="suggested_reply_status"), nullable=False, default=SuggestedReplyStatus.PENDING, index=True)
    generated_by: Mapped[SuggestedReplyGeneratedBy] = mapped_column(Enum(SuggestedReplyGeneratedBy, name="suggested_reply_generated_by"), nullable=False, default=SuggestedReplyGeneratedBy.AGENT)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    edited_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    shop: Mapped[Shop] = relationship(back_populates="suggested_replies")
    conversation: Mapped[Conversation] = relationship(back_populates="suggested_replies")
    message: Mapped[Message | None] = relationship()
    approved_by_user: Mapped[User | None] = relationship()


class AgentDecisionAudit(Base):
    __tablename__ = "agent_decision_audits"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True)
    input_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_intent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extracted_slots: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    product_candidates: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    chosen_product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    variant_resolver_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    inventory_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    next_state: Mapped[str] = mapped_column(String(128), nullable=False)
    outbound_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class FailedJob(Base):
    __tablename__ = "failed_jobs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    queue_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class AdminAuditLog(Base):
    """Immutable audit trail for admin and system actions (audit_logs)."""

    __tablename__ = "admin_audit_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
