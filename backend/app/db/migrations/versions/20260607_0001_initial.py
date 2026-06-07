"""Sprint 1 core schema

Revision ID: 20260607_0001
Revises:
Create Date: 2026-06-07 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260607_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = postgresql.ENUM("owner", "admin", "operator", name="user_role", create_type=False)
shop_member_role = postgresql.ENUM("owner", "admin", "operator", name="shop_member_role", create_type=False)
shop_status = postgresql.ENUM("active", "suspended", name="shop_status", create_type=False)
instagram_account_status = postgresql.ENUM(
    "connected", "disconnected", "expired", name="instagram_account_status", create_type=False
)
conversation_state = postgresql.ENUM(
    "open", "closed", "pending_handoff", "archived", name="conversation_state", create_type=False
)
message_direction = postgresql.ENUM("inbound", "outbound", name="message_direction", create_type=False)
message_channel = postgresql.ENUM("instagram", name="message_channel", create_type=False)
message_type = postgresql.ENUM(
    "text", "shared_post", "attachment", "system", name="message_type", create_type=False
)
agent_action_status = postgresql.ENUM("success", "failed", name="agent_action_status", create_type=False)


def upgrade() -> None:
    user_role.create(op.get_bind(), checkfirst=True)
    shop_member_role.create(op.get_bind(), checkfirst=True)
    shop_status.create(op.get_bind(), checkfirst=True)
    instagram_account_status.create(op.get_bind(), checkfirst=True)
    conversation_state.create(op.get_bind(), checkfirst=True)
    message_direction.create(op.get_bind(), checkfirst=True)
    message_channel.create(op.get_bind(), checkfirst=True)
    message_type.create(op.get_bind(), checkfirst=True)
    agent_action_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_created_at"), "users", ["created_at"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "shops",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("status", shop_status, nullable=False),
        sa.Column("default_currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shops_created_at"), "shops", ["created_at"], unique=False)
    op.create_index(op.f("ix_shops_slug"), "shops", ["slug"], unique=True)

    op.create_table(
        "shop_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", shop_member_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "user_id", name="uq_shop_members_shop_user"),
    )
    op.create_index(op.f("ix_shop_members_created_at"), "shop_members", ["created_at"], unique=False)
    op.create_index(op.f("ix_shop_members_shop_id"), "shop_members", ["shop_id"], unique=False)
    op.create_index(op.f("ix_shop_members_user_id"), "shop_members", ["user_id"], unique=False)

    op.create_table(
        "instagram_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ig_user_id", sa.String(length=64), nullable=False),
        sa.Column("page_id", sa.String(length=64), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("webhook_enabled", sa.Boolean(), nullable=False),
        sa.Column("status", instagram_account_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "ig_user_id", name="uq_instagram_accounts_shop_ig_user"),
    )
    op.create_index(op.f("ix_instagram_accounts_created_at"), "instagram_accounts", ["created_at"], unique=False)
    op.create_index(op.f("ix_instagram_accounts_ig_user_id"), "instagram_accounts", ["ig_user_id"], unique=False)
    op.create_index(op.f("ix_instagram_accounts_shop_id"), "instagram_accounts", ["shop_id"], unique=False)

    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instagram_user_id", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("postal_code", sa.String(length=32), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "instagram_user_id", name="uq_customers_shop_instagram_user"),
    )
    op.create_index(op.f("ix_customers_created_at"), "customers", ["created_at"], unique=False)
    op.create_index(op.f("ix_customers_instagram_user_id"), "customers", ["instagram_user_id"], unique=False)
    op.create_index(op.f("ix_customers_shop_id"), "customers", ["shop_id"], unique=False)

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instagram_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", conversation_state, nullable=False),
        sa.Column("last_intent", sa.String(length=128), nullable=True),
        sa.Column("assigned_operator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("handoff_required", sa.Boolean(), nullable=False),
        sa.Column("handoff_reason", sa.Text(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_operator_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instagram_account_id"], ["instagram_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversations_assigned_operator_id"), "conversations", ["assigned_operator_id"], unique=False)
    op.create_index(op.f("ix_conversations_created_at"), "conversations", ["created_at"], unique=False)
    op.create_index(op.f("ix_conversations_customer_id"), "conversations", ["customer_id"], unique=False)
    op.create_index(op.f("ix_conversations_instagram_account_id"), "conversations", ["instagram_account_id"], unique=False)
    op.create_index(op.f("ix_conversations_shop_id"), "conversations", ["shop_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", message_direction, nullable=False),
        sa.Column("channel", message_channel, nullable=False),
        sa.Column("instagram_message_id", sa.String(length=128), nullable=True),
        sa.Column("message_type", message_type, nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_messages_conversation_id"), "messages", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_messages_created_at"), "messages", ["created_at"], unique=False)
    op.create_index(op.f("ix_messages_instagram_message_id"), "messages", ["instagram_message_id"], unique=False)

    op.create_table(
        "agent_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_name", sa.String(length=128), nullable=False),
        sa.Column("input_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("status", agent_action_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_actions_conversation_id"), "agent_actions", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_agent_actions_created_at"), "agent_actions", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_table("agent_actions")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("customers")
    op.drop_table("instagram_accounts")
    op.drop_table("shop_members")
    op.drop_table("shops")
    op.drop_table("users")

    agent_action_status.drop(op.get_bind(), checkfirst=True)
    message_type.drop(op.get_bind(), checkfirst=True)
    message_channel.drop(op.get_bind(), checkfirst=True)
    message_direction.drop(op.get_bind(), checkfirst=True)
    conversation_state.drop(op.get_bind(), checkfirst=True)
    instagram_account_status.drop(op.get_bind(), checkfirst=True)
    shop_status.drop(op.get_bind(), checkfirst=True)
    shop_member_role.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
