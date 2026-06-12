"""multi-channel commerce messaging foundation

Revision ID: 20260612_0024
Revises: 20260610_0023
Create Date: 2026-06-12 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260612_0024"
down_revision: str | None = "20260610_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

channel_provider = postgresql.ENUM("instagram", "whatsapp", "telegram", "bale", "rubika", name="channel_provider", create_type=False)
channel_account_status = postgresql.ENUM("draft", "connected", "webhook_configured", "disabled", "error", name="channel_account_status", create_type=False)
channel_conversation_status = postgresql.ENUM("open", "closed", "archived", name="channel_conversation_status", create_type=False)
channel_message_type = postgresql.ENUM("text", "image", "video", "audio", "voice", "document", "location", "contact", "interactive", "button_callback", "order", "payment", "unknown", name="channel_message_type", create_type=False)
message_direction = postgresql.ENUM("inbound", "outbound", name="message_direction", create_type=False)


def upgrade() -> None:
    op.execute("CREATE TYPE channel_provider AS ENUM ('instagram', 'whatsapp', 'telegram', 'bale', 'rubika')")
    op.execute("CREATE TYPE channel_account_status AS ENUM ('draft', 'connected', 'webhook_configured', 'disabled', 'error')")
    op.execute("CREATE TYPE channel_conversation_status AS ENUM ('open', 'closed', 'archived')")
    op.execute("CREATE TYPE channel_message_type AS ENUM ('text', 'image', 'video', 'audio', 'voice', 'document', 'location', 'contact', 'interactive', 'button_callback', 'order', 'payment', 'unknown')")
    op.execute("ALTER TYPE webhook_provider ADD VALUE IF NOT EXISTS 'bale'")
    op.execute("ALTER TYPE webhook_provider ADD VALUE IF NOT EXISTS 'rubika'")
    op.execute("ALTER TYPE message_channel ADD VALUE IF NOT EXISTS 'bale'")
    op.execute("ALTER TYPE message_channel ADD VALUE IF NOT EXISTS 'rubika'")

    op.create_table(
        "channel_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", channel_provider, nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("external_account_id", sa.String(length=128), nullable=True),
        sa.Column("phone_number_id", sa.String(length=128), nullable=True),
        sa.Column("bot_username", sa.String(length=255), nullable=True),
        sa.Column("bot_id", sa.String(length=128), nullable=True),
        sa.Column("webhook_verify_token", sa.String(length=255), nullable=True),
        sa.Column("webhook_secret", sa.Text(), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("encrypted_bot_token", sa.Text(), nullable=True),
        sa.Column("status", channel_account_status, nullable=False, server_default="draft"),
        sa.Column("capabilities_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("settings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "provider", "external_account_id", name="uq_channel_accounts_shop_provider_external"),
    )
    for col in ["shop_id", "provider", "external_account_id", "phone_number_id", "bot_id", "status", "created_at", "updated_at"]:
        op.create_index(op.f(f"ix_channel_accounts_{col}"), "channel_accounts", [col], unique=False)

    op.create_table(
        "channel_contact_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", channel_provider, nullable=False),
        sa.Column("channel_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_user_id", sa.String(length=128), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("raw_profile_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["channel_account_id"], ["channel_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "provider", "channel_account_id", "external_user_id", name="uq_channel_contact_identity_external"),
    )
    for col in ["shop_id", "provider", "channel_account_id", "external_user_id", "customer_id", "created_at", "updated_at"]:
        op.create_index(op.f(f"ix_channel_contact_identities_{col}"), "channel_contact_identities", [col], unique=False)

    op.create_table(
        "channel_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", channel_provider, nullable=False),
        sa.Column("channel_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_chat_id", sa.String(length=128), nullable=False),
        sa.Column("external_thread_id", sa.String(length=128), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("messaging_window_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_inbound_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_outbound_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", channel_conversation_status, nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["channel_account_id"], ["channel_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "channel_account_id", "external_chat_id", "external_thread_id", name="uq_channel_conversation_external"),
    )
    for col in ["shop_id", "provider", "channel_account_id", "external_chat_id", "external_thread_id", "conversation_id", "status", "created_at", "updated_at"]:
        op.create_index(op.f(f"ix_channel_conversations_{col}"), "channel_conversations", [col], unique=False)

    op.create_table(
        "channel_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", channel_provider, nullable=False),
        sa.Column("channel_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("internal_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_message_id", sa.String(length=128), nullable=True),
        sa.Column("external_update_id", sa.String(length=128), nullable=True),
        sa.Column("direction", message_direction, nullable=False),
        sa.Column("message_type", channel_message_type, nullable=False, server_default="unknown"),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("media_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("interactive_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("raw_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("normalized_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("is_simulation", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["channel_account_id"], ["channel_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["internal_message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "channel_account_id", "idempotency_key", name="uq_channel_messages_idempotency"),
    )
    for col in ["shop_id", "provider", "channel_account_id", "conversation_id", "internal_message_id", "external_message_id", "external_update_id", "direction", "idempotency_key", "is_simulation", "created_at"]:
        op.create_index(op.f(f"ix_channel_messages_{col}"), "channel_messages", [col], unique=False)

    op.create_table(
        "provider_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", channel_provider, nullable=False),
        sa.Column("channel_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("raw_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["channel_account_id"], ["channel_accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "idempotency_key", name="uq_provider_webhook_events_idempotency"),
    )

    op.create_table(
        "provider_delivery_statuses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", channel_provider, nullable=False),
        sa.Column("channel_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_message_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("raw_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["channel_message_id"], ["channel_messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute("""
        INSERT INTO channel_accounts (id, shop_id, provider, display_name, external_account_id, bot_username, encrypted_access_token, status, capabilities_json, settings_json, created_at, updated_at)
        SELECT gen_random_uuid(), shop_id, 'instagram'::channel_provider, username, ig_user_id, username, access_token_encrypted, 'connected'::channel_account_status,
               '{"supports_webhook": true, "supports_text": true, "supports_images": true}'::jsonb,
               jsonb_build_object('legacy_instagram_account_id', id::text), now(), now()
        FROM instagram_accounts
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table("provider_delivery_statuses")
    op.drop_table("provider_webhook_events")
    op.drop_table("channel_messages")
    op.drop_table("channel_conversations")
    op.drop_table("channel_contact_identities")
    op.drop_table("channel_accounts")
    op.execute("DROP TYPE channel_message_type")
    op.execute("DROP TYPE channel_conversation_status")
    op.execute("DROP TYPE channel_account_status")
    op.execute("DROP TYPE channel_provider")
