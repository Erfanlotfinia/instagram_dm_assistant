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
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import (
    AgentActionStatus,
    AgentMode,
    AgentRunStatus,
    AgentWorkflowState,
    CatalogAliasSource,
    CatalogImportJobStatus,
    ChannelAccountStatus,
    ChannelConnectionMethod,
    ChannelConnectionProvider,
    ChannelConnectionSessionStatus,
    ConversationResponseMode,
    TelegramConnectionMode,
    TelegramConnectionSessionStatus,
    ChannelConversationStatus,
    ChannelMessageType,
    ChannelProvider,
    ConfidenceSource,
    ConversationEventType,
    ConversationPriorityLevel,
    ConversationState,
    FailedJobStatus,
    OutboxEventStatus,
    InstagramAccountStatus,
    InventoryMovementType,
    InventoryReservationStatus,
    MessageChannel,
    MessageDirection,
    MessageType,
    OperatorReviewDecision,
    OrderCorrectnessAction,
    OrderPaymentStatus,
    OrderTransitionTrigger,
    OrderRecoveryAttemptStatus,
    OrderRecoveryStatus,
    OrderShippingStatus,
    OrderStatus,
    UpsellSuggestionStatus,
    PaymentProvider,
    PaymentRecordStatus,
    ProductStatus,
    ResolverConfidenceBand,
    ResolverFeedbackAction,
    ResolverTraceType,
    ShipmentProvider,
    ShipmentStatus,
    ShopStatus,
    SellingStyle,
    SuggestedReplyGeneratedBy,
    SuggestedReplyStatus,
    TriggerSourceType,
    UserRole,
    VariantAliasType,
    PilotEventSeverity,
    PilotModeScope,
    PilotOperatingMode,
    IncidentSeverity,
    IncidentStatus,
    IncidentTrigger,
    ScenarioPackType,
    SimulatorRunSourceType,
    SimulatorRunStatus,
    TraceEventType,
    WhatsAppTemplateCategory,
    WhatsAppTemplateStatus,
    WebhookDedupeOutcome,
    WebhookProcessingStatus,
    WebhookProvider,
)
from app.domain.mixins import TimestampMixin


def enum_values(enum_cls: type[Any]) -> list[str]:
    return [member.value for member in enum_cls]


def pg_enum(enum_cls: type[Any], name: str, **kwargs: Any) -> Enum:
    return PG_ENUM(
        enum_cls,
        name=name,
        create_type=False,
        values_callable=enum_values,
        **kwargs,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(pg_enum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    shop_memberships: Mapped[list[ShopMember]] = relationship(back_populates="user")
    assigned_conversations: Mapped[list[Conversation]] = relationship(
        back_populates="assigned_operator",
        foreign_keys="Conversation.assigned_operator_id",
    )


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    user: Mapped[User] = relationship()


class Shop(Base, TimestampMixin):
    __tablename__ = "shops"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[ShopStatus] = mapped_column(
        pg_enum(ShopStatus, name="shop_status"), nullable=False, default=ShopStatus.ACTIVE
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
    recovery_rules: Mapped[list[AbandonedOrderRecoveryRule]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    product_upsells: Mapped[list[ProductUpsell]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    trl_validation_runs: Mapped[list[TRLValidationRun]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    pilot_settings: Mapped[PilotSettings | None] = relationship(
        back_populates="shop", cascade="all, delete-orphan", uselist=False
    )
    pilot_events: Mapped[list[PilotEvent]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    simulator_runs: Mapped[list["SimulatorRun"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    policy_versions: Mapped[list["PolicyVersion"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    scenario_packs: Mapped[list["ScenarioPack"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    incidents: Mapped[list["Incident"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )


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
    role: Mapped[UserRole] = mapped_column(pg_enum(UserRole, name="shop_member_role"), nullable=False)
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
        pg_enum(InstagramAccountStatus, name="instagram_account_status"),
        nullable=False,
        default=InstagramAccountStatus.CONNECTED,
    )

    shop: Mapped[Shop] = relationship(back_populates="instagram_accounts")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="instagram_account")


class ChannelAccount(Base, TimestampMixin):
    __tablename__ = "channel_accounts"
    __table_args__ = (UniqueConstraint("shop_id", "provider", "external_account_id", name="uq_channel_accounts_shop_provider_external"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[ChannelProvider] = mapped_column(pg_enum(ChannelProvider, name="channel_provider"), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_account_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    phone_number_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    bot_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bot_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_verify_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webhook_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    bot_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes_json: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[ChannelAccountStatus] = mapped_column(pg_enum(ChannelAccountStatus, name="channel_account_status"), nullable=False, default=ChannelAccountStatus.DRAFT, index=True)
    capabilities_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    settings_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    last_validation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    connection_mode: Mapped[TelegramConnectionMode | None] = mapped_column(
        pg_enum(TelegramConnectionMode, name="telegram_connection_mode"),
        nullable=True,
        index=True,
    )
    telegram_business_connection_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    telegram_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    telegram_rights_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    telegram_capabilities_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    telegram_last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    telegram_business_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    managed_bot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    manager_bot_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    managed_bot_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)


class TelegramConnectionSession(Base, TimestampMixin):
    __tablename__ = "telegram_connection_sessions"
    __table_args__ = (UniqueConstraint("state", name="uq_telegram_connection_sessions_state"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("channel_accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    mode: Mapped[TelegramConnectionMode] = mapped_column(
        pg_enum(TelegramConnectionMode, name="telegram_connection_mode"),
        nullable=False,
    )
    status: Mapped[TelegramConnectionSessionStatus] = mapped_column(
        pg_enum(TelegramConnectionSessionStatus, name="telegram_connection_session_status"),
        nullable=False,
        default=TelegramConnectionSessionStatus.PENDING,
        index=True,
    )
    state: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ChannelConnectionSession(Base, TimestampMixin):
    __tablename__ = "channel_connection_sessions"
    __table_args__ = (UniqueConstraint("state", name="uq_channel_connection_sessions_state"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[ChannelConnectionProvider] = mapped_column(
        pg_enum(ChannelConnectionProvider, name="channel_connection_provider"),
        nullable=False,
        index=True,
    )
    method: Mapped[ChannelConnectionMethod] = mapped_column(
        pg_enum(ChannelConnectionMethod, name="channel_connection_method"),
        nullable=False,
    )
    status: Mapped[ChannelConnectionSessionStatus] = mapped_column(
        pg_enum(ChannelConnectionSessionStatus, name="channel_connection_session_status"),
        nullable=False,
        default=ChannelConnectionSessionStatus.PENDING,
        index=True,
    )
    state: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    nonce: Mapped[str] = mapped_column(String(128), nullable=False)
    code_verifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    requested_scopes_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    provider_payload_redacted: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    oauth_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_external_account_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    selected_page_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    selected_instagram_business_account_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ChannelContactIdentity(Base, TimestampMixin):
    __tablename__ = "channel_contact_identities"
    __table_args__ = (UniqueConstraint("shop_id", "provider", "channel_account_id", "external_user_id", name="uq_channel_contact_identity_external"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[ChannelProvider] = mapped_column(pg_enum(ChannelProvider, name="channel_provider"), nullable=False, index=True)
    channel_account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("channel_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    external_user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    external_chat_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_profile_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    customer_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)


class ChannelConversation(Base, TimestampMixin):
    __tablename__ = "channel_conversations"
    __table_args__ = (UniqueConstraint("provider", "channel_account_id", "external_chat_id", "external_thread_id", name="uq_channel_conversation_external"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[ChannelProvider] = mapped_column(pg_enum(ChannelProvider, name="channel_provider"), nullable=False, index=True)
    channel_account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("channel_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    external_chat_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    external_thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    messaging_window_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_outbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[ChannelConversationStatus] = mapped_column(pg_enum(ChannelConversationStatus, name="channel_conversation_status"), nullable=False, default=ChannelConversationStatus.OPEN, index=True)


class ChannelMessage(Base):
    __tablename__ = "channel_messages"
    __table_args__ = (UniqueConstraint("provider", "channel_account_id", "idempotency_key", name="uq_channel_messages_idempotency"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[ChannelProvider] = mapped_column(pg_enum(ChannelProvider, name="channel_provider"), nullable=False, index=True)
    channel_account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("channel_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    internal_message_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True)
    external_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    external_update_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    direction: Mapped[MessageDirection] = mapped_column(pg_enum(MessageDirection, name="message_direction"), nullable=False, index=True)
    message_type: Mapped[ChannelMessageType] = mapped_column(pg_enum(ChannelMessageType, name="channel_message_type"), nullable=False, default=ChannelMessageType.UNKNOWN)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    interactive_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    raw_payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    normalized_payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    is_simulation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class ChannelDeliveryStatusEvent(Base):
    __tablename__ = "channel_delivery_status_events"
    __table_args__ = (UniqueConstraint("provider", "channel_account_id", "external_message_id", "status", name="uq_channel_delivery_status_event"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[ChannelProvider] = mapped_column(pg_enum(ChannelProvider, name="channel_provider"), nullable=False, index=True)
    channel_account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("channel_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    external_message_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    external_chat_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class WhatsAppMessageTemplate(Base, TimestampMixin):
    __tablename__ = "whatsapp_message_templates"
    __table_args__ = (UniqueConstraint("shop_id", "channel_account_id", "template_name", "language_code", name="uq_whatsapp_template_name_language"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("channel_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    template_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    language_code: Mapped[str] = mapped_column(String(16), nullable=False, default="en_US", index=True)
    category: Mapped[WhatsAppTemplateCategory] = mapped_column(pg_enum(WhatsAppTemplateCategory, name="whatsapp_template_category"), nullable=False, default=WhatsAppTemplateCategory.UNKNOWN, index=True)
    status: Mapped[WhatsAppTemplateStatus] = mapped_column(pg_enum(WhatsAppTemplateStatus, name="whatsapp_template_status"), nullable=False, default=WhatsAppTemplateStatus.DRAFT, index=True)
    components_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    external_template_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    primary_channel_provider: Mapped[ChannelProvider | None] = mapped_column(
        pg_enum(ChannelProvider, name="channel_provider"), nullable=True, index=True
    )
    primary_external_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    # Legacy profile fields remain nullable during the compatibility window.
    instagram_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    shop: Mapped[Shop] = relationship(back_populates="customers")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="customer")
    orders: Mapped[list[Order]] = relationship(back_populates="customer")
    preferences: Mapped[CustomerPreferences | None] = relationship(
        back_populates="customer", cascade="all, delete-orphan", uselist=False
    )
    channel_identities: Mapped[list[ChannelContactIdentity]] = relationship(
        cascade="all, delete-orphan"
    )


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instagram_account_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("instagram_accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    channel_account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("channel_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="instagram", index=True)
    external_conversation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    external_thread_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    channel_conversation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    channel_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    trigger_rule_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("comment_to_dm_triggers.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state: Mapped[ConversationState] = mapped_column(
        pg_enum(ConversationState, name="conversation_state"),
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
        pg_enum(AgentWorkflowState, name="agent_workflow_state"),
        nullable=False,
        default=AgentWorkflowState.IDLE,
    )
    agent_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    agent_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    response_mode: Mapped[ConversationResponseMode] = mapped_column(
        pg_enum(ConversationResponseMode, name="conversation_response_mode"),
        nullable=False,
        default=ConversationResponseMode.AI,
        index=True,
    )
    is_simulation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    suggested_outbound: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    preview_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    priority_level: Mapped[ConversationPriorityLevel] = mapped_column(
        pg_enum(ConversationPriorityLevel, name="conversation_priority_level"),
        nullable=False,
        default=ConversationPriorityLevel.LOW,
        index=True,
    )
    priority_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_operator_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    needs_attention: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    shop: Mapped[Shop] = relationship(back_populates="conversations")
    instagram_account: Mapped[InstagramAccount | None] = relationship(back_populates="conversations")
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
    events: Mapped[list[ConversationEvent]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class ConversationEvent(Base):
    __tablename__ = "conversation_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[ConversationEventType] = mapped_column(
        pg_enum(ConversationEventType, name="conversation_event_type"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    conversation: Mapped[Conversation] = relationship(back_populates="events")
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_user_id])


class WebhookEvent(Base, TimestampMixin):
    __tablename__ = "webhook_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[WebhookProvider] = mapped_column(
        pg_enum(WebhookProvider, name="webhook_provider"), nullable=False
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
        pg_enum(WebhookProcessingStatus, name="webhook_processing_status"),
        nullable=False,
        default=WebhookProcessingStatus.RECEIVED,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dedupe_outcome: Mapped[WebhookDedupeOutcome | None] = mapped_column(
        pg_enum(WebhookDedupeOutcome, name="webhook_dedupe_outcome"), nullable=True
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    aggregate_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aggregate_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    shop_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[OutboxEventStatus] = mapped_column(
        pg_enum(OutboxEventStatus, name="outbox_event_status"),
        nullable=False,
        default=OutboxEventStatus.PENDING,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("instagram_message_id", name="uq_messages_instagram_message_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction: Mapped[MessageDirection] = mapped_column(
        pg_enum(MessageDirection, name="message_direction"), nullable=False
    )
    customer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    channel_provider: Mapped[ChannelProvider] = mapped_column(
        pg_enum(ChannelProvider, name="channel_provider"), nullable=False, index=True
    )
    channel_account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("channel_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    external_update_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    channel: Mapped[MessageChannel] = mapped_column(
        pg_enum(MessageChannel, name="message_channel"), nullable=False, default=MessageChannel.INSTAGRAM
    )
    instagram_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    channel_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    raw_channel_payload_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("raw_channel_payloads.id", ondelete="SET NULL"), nullable=True, index=True)
    message_type: Mapped[MessageType] = mapped_column(pg_enum(MessageType, name="message_type"), nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    raw_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    normalized_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_simulation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
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
        pg_enum(AgentActionStatus, name="agent_action_status"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    conversation: Mapped[Conversation] = relationship(back_populates="agent_actions")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        UniqueConstraint("input_message_id", name="uq_agent_runs_input_message_id"),
    )

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
        pg_enum(AgentRunStatus, name="agent_run_status"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_simulation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
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


class ProductCategory(Base, TimestampMixin):
    __tablename__ = "product_categories"
    __table_args__ = (UniqueConstraint("shop_id", "slug", name="uq_product_categories_shop_slug"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    parent_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class CatalogAttributeDefinition(Base, TimestampMixin):
    __tablename__ = "catalog_attribute_definitions"
    __table_args__ = (UniqueConstraint("shop_id", "category_id", "slug", name="uq_catalog_attribute_definitions_scope_slug"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=True, index=True)
    category_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("product_categories.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_variant_defining: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_searchable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    allowed_values_json: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    aliases_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class ProductAttribute(Base, TimestampMixin):
    __tablename__ = "product_attributes"
    __table_args__ = (UniqueConstraint("product_id", "attribute_definition_id", name="uq_product_attributes_product_definition"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute_definition_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("catalog_attribute_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    value_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    normalized_value_json: Mapped[Any | None] = mapped_column(JSONB, nullable=True)


class VariantAttribute(Base, TimestampMixin):
    __tablename__ = "variant_attributes"
    __table_args__ = (UniqueConstraint("product_variant_id", "attribute_definition_id", name="uq_variant_attributes_variant_definition"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    product_variant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False, index=True)
    attribute_definition_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("catalog_attribute_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    value_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    normalized_value_json: Mapped[Any | None] = mapped_column(JSONB, nullable=True)


class AttributeAlias(Base, TimestampMixin):
    __tablename__ = "attribute_aliases"
    __table_args__ = (UniqueConstraint("shop_id", "attribute_definition_id", "raw_value", "language", name="uq_attribute_aliases_scope_raw_language"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=True, index=True)
    attribute_definition_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("catalog_attribute_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_value: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    normalized_value: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    confidence: Mapped[Any] = mapped_column(Numeric(4, 3), nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


class CategoryPreset(Base, TimestampMixin):
    __tablename__ = "category_presets"
    __table_args__ = (UniqueConstraint("slug", name="uq_category_presets_slug"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    preset_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_system_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        pg_enum(ProductStatus, name="product_status"), nullable=False, default=ProductStatus.ACTIVE
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
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

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
        pg_enum(ConfidenceSource, name="confidence_source"), nullable=False, default=ConfidenceSource.MANUAL
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
    provider: Mapped[MessageChannel] = mapped_column(pg_enum(MessageChannel, name="message_channel"), nullable=False, index=True)
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
    source_type: Mapped[TriggerSourceType] = mapped_column(pg_enum(TriggerSourceType, name="trigger_source_type"), nullable=False, default=TriggerSourceType.COMMENT, index=True)
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
    source_type: Mapped[TriggerSourceType] = mapped_column(pg_enum(TriggerSourceType, name="trigger_source_type"), nullable=False)
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
        pg_enum(InventoryMovementType, name="inventory_movement_type"), nullable=False
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
        pg_enum(OrderStatus, name="order_status"), nullable=False, default=OrderStatus.DRAFT, index=True
    )
    subtotal_amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    shipping_amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    discount_amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payment_status: Mapped[OrderPaymentStatus] = mapped_column(
        pg_enum(OrderPaymentStatus, name="order_payment_status"),
        nullable=False,
        default=OrderPaymentStatus.UNPAID,
        index=True,
    )
    shipping_status: Mapped[OrderShippingStatus] = mapped_column(
        pg_enum(OrderShippingStatus, name="order_shipping_status"),
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
    recovery_status: Mapped[OrderRecoveryStatus] = mapped_column(
        pg_enum(OrderRecoveryStatus, name="order_recovery_status"),
        nullable=False,
        default=OrderRecoveryStatus.NONE,
        index=True,
    )
    recovery_attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_recovery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_simulation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    customer_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    customer_confirmation_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    admin_override_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_confirmed_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    inventory_finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence_score: Mapped[Any | None] = mapped_column(Numeric(5, 4), nullable=True)
    confidence_source: Mapped[ConfidenceSource | None] = mapped_column(
        pg_enum(ConfidenceSource, name="confidence_source"), nullable=True
    )
    active_reservation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("inventory_reservations.id", ondelete="SET NULL"),
        nullable=True,
    )
    pilot_mode_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(256), nullable=True)

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
    recovery_attempts: Mapped[list[OrderRecoveryAttempt]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    draft_items: Mapped[list[OrderItemDraft]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    active_reservation: Mapped[InventoryReservation | None] = relationship(
        foreign_keys=[active_reservation_id],
    )
    inventory_reservations: Mapped[list[InventoryReservation]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        foreign_keys="InventoryReservation.order_id",
    )


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"
    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "product_variant_id",
            name="uq_inventory_reservations_active_order_variant",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_variant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[InventoryReservationStatus] = mapped_column(
        pg_enum(InventoryReservationStatus, name="inventory_reservation_status"),
        nullable=False,
        default=InventoryReservationStatus.ACTIVE,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped[Order] = relationship(
        back_populates="inventory_reservations",
        foreign_keys=[order_id],
    )


class OrderItemDraft(Base):
    __tablename__ = "order_items_draft"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    product_variant_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    product_title_snapshot: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    variant_label_snapshot: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    unit_price: Mapped[Any] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped[Order] = relationship(back_populates="draft_items")


class OrderStateTransition(Base):
    __tablename__ = "order_state_transitions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str] = mapped_column(String(64), nullable=False)
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger: Mapped[OrderTransitionTrigger] = mapped_column(
        pg_enum(OrderTransitionTrigger, name="order_transition_trigger"), nullable=False
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    transition_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ActionAttempt(Base):
    __tablename__ = "action_attempts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[OrderCorrectnessAction] = mapped_column(
        pg_enum(OrderCorrectnessAction, name="order_correctness_action"), nullable=False
    )
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    denial_reasons: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    policy_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PilotMode(Base):
    __tablename__ = "pilot_modes"
    __table_args__ = (UniqueConstraint("shop_id", "action", name="uq_pilot_modes_shop_action"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[OrderCorrectnessAction] = mapped_column(
        pg_enum(OrderCorrectnessAction, name="order_correctness_action"), nullable=False
    )
    permitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    confidence_threshold: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=False, default=0.6)
    require_customer_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class OperatorReview(Base):
    __tablename__ = "operator_reviews"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[OperatorReviewDecision] = mapped_column(
        pg_enum(OperatorReviewDecision, name="operator_review_decision"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
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
        pg_enum(PaymentProvider, name="payment_provider"), nullable=False
    )
    status: Mapped[PaymentRecordStatus] = mapped_column(
        pg_enum(PaymentRecordStatus, name="payment_record_status"),
        nullable=False,
        default=PaymentRecordStatus.CREATED,
        index=True,
    )
    payment_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    callback_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    order: Mapped[Order] = relationship(back_populates="payments")


class Shipment(Base, TimestampMixin):
    __tablename__ = "shipments"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[ShipmentProvider] = mapped_column(
        pg_enum(ShipmentProvider, name="shipment_provider"), nullable=False, default=ShipmentProvider.MANUAL
    )
    status: Mapped[ShipmentStatus] = mapped_column(
        pg_enum(ShipmentStatus, name="shipment_status"),
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
    normalized_slots: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    product_candidates: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    selected_product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    variant_resolution: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    inventory_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    risk_score: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
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
    mode: Mapped[AgentMode] = mapped_column(pg_enum(AgentMode, name="agent_mode"), nullable=False, default=AgentMode.COPILOT)
    selling_style: Mapped[SellingStyle] = mapped_column(pg_enum(SellingStyle, name="selling_style"), nullable=False, default=SellingStyle.FRIENDLY)
    discount_policy_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    handoff_policy_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    risk_policy_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
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
    status: Mapped[SuggestedReplyStatus] = mapped_column(pg_enum(SuggestedReplyStatus, name="suggested_reply_status"), nullable=False, default=SuggestedReplyStatus.PENDING, index=True)
    generated_by: Mapped[SuggestedReplyGeneratedBy] = mapped_column(pg_enum(SuggestedReplyGeneratedBy, name="suggested_reply_generated_by"), nullable=False, default=SuggestedReplyGeneratedBy.AGENT)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    edited_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_simulation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
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
    normalized_slots: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    product_candidates: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    chosen_product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    variant_resolver_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    inventory_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    next_state: Mapped[str] = mapped_column(String(128), nullable=False)
    outbound_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class FailedJob(Base, TimestampMixin):
    __tablename__ = "failed_jobs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=True, index=True
    )
    queue_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    traceback: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    status: Mapped[FailedJobStatus] = mapped_column(
        pg_enum(FailedJobStatus, name="failed_job_status"), nullable=False, default=FailedJobStatus.FAILED, index=True
    )
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


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


class AbandonedOrderRecoveryRule(Base, TimestampMixin):
    __tablename__ = "abandoned_order_recovery_rules"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    trigger_after_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    only_inside_allowed_messaging_window: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    shop: Mapped[Shop] = relationship(back_populates="recovery_rules")


class OrderRecoveryAttempt(Base):
    __tablename__ = "order_recovery_attempts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[OrderRecoveryAttemptStatus] = mapped_column(
        pg_enum(OrderRecoveryAttemptStatus, name="order_recovery_attempt_status"),
        nullable=False,
        default=OrderRecoveryAttemptStatus.CREATED,
        index=True,
    )
    skip_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    order: Mapped[Order] = relationship(back_populates="recovery_attempts")
    conversation: Mapped[Conversation] = relationship()


class CustomerPreferences(Base):
    __tablename__ = "customer_preferences"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    preferred_size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preferred_colors: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    preferred_categories: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    last_successful_size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_successful_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_successful_address_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    customer: Mapped[Customer] = relationship(back_populates="preferences")


class ProductUpsell(Base, TimestampMixin):
    __tablename__ = "product_upsells"
    __table_args__ = (
        UniqueConstraint("shop_id", "source_product_id", "target_product_id", name="uq_product_upsells_shop_source_target"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    shop: Mapped[Shop] = relationship(back_populates="product_upsells")
    source_product: Mapped[Product] = relationship(foreign_keys=[source_product_id])
    target_product: Mapped[Product] = relationship(foreign_keys=[target_product_id])


class UpsellSuggestion(Base, TimestampMixin):
    __tablename__ = "upsell_suggestions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    suggested_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[UpsellSuggestionStatus] = mapped_column(
        pg_enum(UpsellSuggestionStatus, name="upsell_suggestion_status"),
        nullable=False,
        default=UpsellSuggestionStatus.SUGGESTED,
        index=True,
    )


class PilotSettings(Base, TimestampMixin):
    __tablename__ = "pilot_settings"

    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), primary_key=True
    )
    pilot_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    pilot_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Pilot")
    pilot_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pilot_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_auto_sent_messages_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    max_auto_created_orders_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    require_operator_approval_for_first_50_orders: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allowed_instagram_account_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    allowed_product_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    emergency_stop_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    operating_mode: Mapped[PilotOperatingMode] = mapped_column(
        pg_enum(PilotOperatingMode, name="pilot_operating_mode"),
        nullable=False,
        default=PilotOperatingMode.COPILOT,
    )
    category_overrides_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    campaign_overrides_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    shop: Mapped[Shop] = relationship(back_populates="pilot_settings")


class PilotEvent(Base):
    __tablename__ = "pilot_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    severity: Mapped[PilotEventSeverity] = mapped_column(
        pg_enum(PilotEventSeverity, name="pilot_event_severity"), nullable=False, default=PilotEventSeverity.INFO, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    shop: Mapped[Shop] = relationship(back_populates="pilot_events")


class TRLValidationRun(Base):
    __tablename__ = "trl_validation_runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    validation_mode: Mapped[str] = mapped_column(
        String(64), nullable=False, default="deterministic_regression", index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running", index=True)
    total_scenarios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_scenarios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_scenarios: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    shop: Mapped[Shop] = relationship(back_populates="trl_validation_runs")
    created_by_user: Mapped[User | None] = relationship()
    scenario_results: Mapped[list[TRLValidationScenarioResult]] = relationship(back_populates="run", cascade="all, delete-orphan")


class TRLValidationScenarioResult(Base):
    __tablename__ = "trl_validation_scenario_results"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("trl_validation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    expected_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    actual_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    failure_reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    order_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    run: Mapped[TRLValidationRun] = relationship(back_populates="scenario_results")
    conversation: Mapped[Conversation | None] = relationship()
    order: Mapped[Order | None] = relationship()


class ProductNormalized(Base, TimestampMixin):
    __tablename__ = "products_normalized"
    __table_args__ = (UniqueConstraint("product_id", name="uq_products_normalized_product_id"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    normalized_title: Mapped[str] = mapped_column(String(512), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    color: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    material: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    collection: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    synonym_candidates: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    qdrant_variant_point_ids: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    dense_vector_dim: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_normalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped[Product] = relationship()
    aliases: Mapped[list[ProductAlias]] = relationship(back_populates="normalized_product", cascade="all, delete-orphan")


class ProductAlias(Base, TimestampMixin):
    __tablename__ = "product_aliases"
    __table_args__ = (
        UniqueConstraint("shop_id", "alias_text", name="uq_product_aliases_shop_alias"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    normalized_product_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("products_normalized.id", ondelete="SET NULL"), nullable=True, index=True
    )
    alias_text: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="und")
    source: Mapped[CatalogAliasSource] = mapped_column(
        pg_enum(CatalogAliasSource, name="catalog_alias_source"), nullable=False, default=CatalogAliasSource.MANUAL
    )
    confidence: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=False, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    normalized_product: Mapped[ProductNormalized | None] = relationship(back_populates="aliases")
    product: Mapped[Product] = relationship()


class VariantAlias(Base, TimestampMixin):
    __tablename__ = "variant_aliases"
    __table_args__ = (
        UniqueConstraint("shop_id", "variant_id", "alias_text", name="uq_variant_aliases_shop_variant_alias"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias_text: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    alias_type: Mapped[VariantAliasType] = mapped_column(
        pg_enum(VariantAliasType, name="variant_alias_type"), nullable=False, default=VariantAliasType.COMBINED
    )
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="und")
    source: Mapped[CatalogAliasSource] = mapped_column(
        pg_enum(CatalogAliasSource, name="catalog_alias_source"), nullable=False, default=CatalogAliasSource.MANUAL
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    variant: Mapped[ProductVariant] = relationship()


class CatalogImportJob(Base, TimestampMixin):
    __tablename__ = "catalog_import_jobs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[CatalogImportJobStatus] = mapped_column(
        pg_enum(CatalogImportJobStatus, name="catalog_import_job_status"),
        nullable=False,
        default=CatalogImportJobStatus.PENDING,
        index=True,
    )
    source_format: Mapped[str] = mapped_column(String(32), nullable=False, default="json")
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checkpoint: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )


class ResolverTrace(Base):
    __tablename__ = "resolver_traces"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trace_type: Mapped[ResolverTraceType] = mapped_column(
        pg_enum(ResolverTraceType, name="resolver_trace_type"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    top_candidates: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    matched_aliases: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    rules_fired: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    missing_slots: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    confidence_band: Mapped[ResolverConfidenceBand] = mapped_column(
        pg_enum(ResolverConfidenceBand, name="resolver_confidence_band"), nullable=False, index=True
    )
    confidence_score: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    qdrant_query_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    feedback_entries: Mapped[list[ResolverFeedback]] = relationship(
        back_populates="trace", cascade="all, delete-orphan"
    )


class ResolverFeedback(Base):
    __tablename__ = "resolver_feedback"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("resolver_traces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[ResolverFeedbackAction] = mapped_column(
        pg_enum(ResolverFeedbackAction, name="resolver_feedback_action"), nullable=False, index=True
    )
    operator_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    corrected_product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    original_variant_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    corrected_variant_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    trace: Mapped[ResolverTrace] = relationship(back_populates="feedback_entries")
    operator: Mapped[User] = relationship()


class BrandSizeMap(Base, TimestampMixin):
    __tablename__ = "brand_size_maps"
    __table_args__ = (
        UniqueConstraint("shop_id", "brand", "raw_size", name="uq_brand_size_maps_shop_brand_raw"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    brand: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    raw_size: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_size: Mapped[str] = mapped_column(String(64), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MediaProductLink(Base, TimestampMixin):
    __tablename__ = "media_product_links"
    __table_args__ = (
        UniqueConstraint("shop_id", "media_id", "product_id", name="uq_media_product_links_shop_media_product"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    media_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    media_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    link_source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    confidence: Mapped[Any] = mapped_column(Numeric(5, 4), nullable=False, default=1.0)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    product: Mapped[Product] = relationship()


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    __table_args__ = (UniqueConstraint("shop_id", "version", name="uq_policy_versions_shop_version"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    shop: Mapped[Shop] = relationship()
    created_by_user: Mapped[User | None] = relationship()
    simulator_runs: Mapped[list["SimulatorRun"]] = relationship(back_populates="policy_version")


class SimulatorRun(Base):
    __tablename__ = "simulator_runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[SimulatorRunSourceType] = mapped_column(
        pg_enum(SimulatorRunSourceType, name="simulator_run_source_type"),
        nullable=False,
        default=SimulatorRunSourceType.MANUAL,
        index=True,
    )
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("policy_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    catalog_snapshot_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    catalog_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[SimulatorRunStatus] = mapped_column(
        pg_enum(SimulatorRunStatus, name="simulator_run_status"),
        nullable=False,
        default=SimulatorRunStatus.RUNNING,
        index=True,
    )
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    diff_summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    shop: Mapped[Shop] = relationship()
    created_by_user: Mapped[User | None] = relationship()
    policy_version: Mapped[PolicyVersion | None] = relationship(back_populates="simulator_runs")
    items: Mapped[list["SimulatorRunItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class SimulatorRunItem(Base):
    __tablename__ = "simulator_run_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("simulator_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    expected_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    actual_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    diff_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    trace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    run: Mapped[SimulatorRun] = relationship(back_populates="items")
    conversation: Mapped[Conversation | None] = relationship()


class TraceEvent(Base):
    __tablename__ = "trace_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    trace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    event_type: Mapped[TraceEventType] = mapped_column(
        pg_enum(TraceEventType, name="trace_event_type"), nullable=False, index=True
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    shop: Mapped[Shop] = relationship()
    conversation: Mapped[Conversation | None] = relationship()


class ScenarioPack(Base, TimestampMixin):
    __tablename__ = "scenario_packs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    pack_type: Mapped[ScenarioPackType] = mapped_column(
        pg_enum(ScenarioPackType, name="scenario_pack_type"), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scenarios_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    is_golden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    shop: Mapped[Shop] = relationship()
    created_by_user: Mapped[User | None] = relationship()


class PilotModeHistory(Base):
    __tablename__ = "pilot_mode_history"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_mode: Mapped[PilotOperatingMode | None] = mapped_column(
        pg_enum(PilotOperatingMode, name="pilot_operating_mode"), nullable=True
    )
    new_mode: Mapped[PilotOperatingMode] = mapped_column(
        pg_enum(PilotOperatingMode, name="pilot_operating_mode"), nullable=False
    )
    scope: Mapped[PilotModeScope] = mapped_column(
        pg_enum(PilotModeScope, name="pilot_mode_scope"), nullable=False, default=PilotModeScope.GLOBAL
    )
    scope_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    changed_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    shop: Mapped[Shop] = relationship()
    changed_by_user: Mapped[User | None] = relationship()


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[IncidentSeverity] = mapped_column(
        pg_enum(IncidentSeverity, name="incident_severity"), nullable=False, index=True
    )
    status: Mapped[IncidentStatus] = mapped_column(
        pg_enum(IncidentStatus, name="incident_status"), nullable=False, default=IncidentStatus.OPEN, index=True
    )
    trigger: Mapped[IncidentTrigger] = mapped_column(
        pg_enum(IncidentTrigger, name="incident_trigger"), nullable=False, index=True
    )
    opened_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    shop: Mapped[Shop] = relationship()
    opened_by_user: Mapped[User | None] = relationship()
    events: Mapped[list["IncidentEvent"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    incident_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    affected_conversation_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    incident: Mapped[Incident] = relationship(back_populates="events")
    actor_user: Mapped[User | None] = relationship()

class ConversationContextItem(Base):
    __tablename__ = "conversation_context_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    channel_account_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    item_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_message_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True)
    external_reference_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    candidate_product_ids_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    selected_product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    selected_variant_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True, index=True)
    attributes_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=1)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class ConversationReferenceLink(Base):
    __tablename__ = "conversation_reference_links"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    from_message_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    to_context_item_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversation_context_items.id", ondelete="CASCADE"), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class AdminTask(Base, TimestampMixin):
    __tablename__ = "admin_tasks"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)


class OperatorCorrection(Base):
    __tablename__ = "operator_corrections"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True)
    correction_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    before_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    after_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    operator_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class AutomationRuleSuggestion(Base):
    __tablename__ = "automation_rule_suggestions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    shop_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), nullable=False, index=True)
    source_correction_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("operator_corrections.id", ondelete="SET NULL"), nullable=True, index=True)
    suggested_rule_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
