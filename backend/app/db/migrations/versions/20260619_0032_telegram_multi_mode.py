"""telegram multi-mode connection support

Revision ID: 20260619_0032
Revises: 20260619_0031
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260619_0032"
down_revision: str | None = "20260619_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

telegram_connection_mode = postgresql.ENUM(
    "bot", "business", "hybrid", name="telegram_connection_mode", create_type=False
)
telegram_connection_session_status = postgresql.ENUM(
    "pending",
    "waiting_bot_token",
    "waiting_business_connection",
    "connected",
    "failed",
    "expired",
    name="telegram_connection_session_status",
    create_type=False,
)
conversation_response_mode = postgresql.ENUM(
    "ai", "human", "hybrid", "paused", name="conversation_response_mode", create_type=False
)


def upgrade() -> None:
    op.execute("ALTER TYPE channel_account_status ADD VALUE IF NOT EXISTS 'disconnected'")
    op.execute("CREATE TYPE telegram_connection_mode AS ENUM ('bot', 'business', 'hybrid')")
    op.execute(
        "CREATE TYPE telegram_connection_session_status AS ENUM ("
        "'pending', 'waiting_bot_token', 'waiting_business_connection', "
        "'connected', 'failed', 'expired')"
    )
    op.execute(
        "CREATE TYPE conversation_response_mode AS ENUM ('ai', 'human', 'hybrid', 'paused')"
    )

    op.add_column(
        "channel_accounts",
        sa.Column("connection_mode", telegram_connection_mode, nullable=True),
    )
    op.add_column(
        "channel_accounts",
        sa.Column("telegram_business_connection_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "channel_accounts",
        sa.Column("telegram_user_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "channel_accounts",
        sa.Column("telegram_username", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "channel_accounts",
        sa.Column("telegram_chat_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "channel_accounts",
        sa.Column(
            "telegram_rights_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "channel_accounts",
        sa.Column(
            "telegram_capabilities_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "channel_accounts",
        sa.Column("telegram_last_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "channel_accounts",
        sa.Column(
            "telegram_business_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        op.f("ix_channel_accounts_connection_mode"),
        "channel_accounts",
        ["connection_mode"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_accounts_telegram_business_connection_id"),
        "channel_accounts",
        ["telegram_business_connection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_accounts_telegram_user_id"),
        "channel_accounts",
        ["telegram_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_accounts_telegram_chat_id"),
        "channel_accounts",
        ["telegram_chat_id"],
        unique=False,
    )

    op.execute(
        "UPDATE channel_accounts SET connection_mode = 'bot' "
        "WHERE provider = 'telegram' AND connection_mode IS NULL"
    )

    op.create_table(
        "telegram_connection_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mode", telegram_connection_mode, nullable=False),
        sa.Column(
            "status",
            telegram_connection_session_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["channel_account_id"], ["channel_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state", name="uq_telegram_connection_sessions_state"),
    )
    op.create_index(
        op.f("ix_telegram_connection_sessions_shop_id"),
        "telegram_connection_sessions",
        ["shop_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_telegram_connection_sessions_channel_account_id"),
        "telegram_connection_sessions",
        ["channel_account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_telegram_connection_sessions_status"),
        "telegram_connection_sessions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_telegram_connection_sessions_state"),
        "telegram_connection_sessions",
        ["state"],
        unique=False,
    )
    op.create_index(
        op.f("ix_telegram_connection_sessions_expires_at"),
        "telegram_connection_sessions",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_telegram_connection_sessions_created_by"),
        "telegram_connection_sessions",
        ["created_by"],
        unique=False,
    )

    op.add_column(
        "conversations",
        sa.Column(
            "response_mode",
            conversation_response_mode,
            nullable=False,
            server_default="ai",
        ),
    )
    op.create_index(
        op.f("ix_conversations_response_mode"),
        "conversations",
        ["response_mode"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_conversations_response_mode"), table_name="conversations")
    op.drop_column("conversations", "response_mode")

    op.drop_index(
        op.f("ix_telegram_connection_sessions_created_by"),
        table_name="telegram_connection_sessions",
    )
    op.drop_index(
        op.f("ix_telegram_connection_sessions_expires_at"),
        table_name="telegram_connection_sessions",
    )
    op.drop_index(
        op.f("ix_telegram_connection_sessions_state"),
        table_name="telegram_connection_sessions",
    )
    op.drop_index(
        op.f("ix_telegram_connection_sessions_status"),
        table_name="telegram_connection_sessions",
    )
    op.drop_index(
        op.f("ix_telegram_connection_sessions_channel_account_id"),
        table_name="telegram_connection_sessions",
    )
    op.drop_index(
        op.f("ix_telegram_connection_sessions_shop_id"),
        table_name="telegram_connection_sessions",
    )
    op.drop_table("telegram_connection_sessions")

    op.drop_index(op.f("ix_channel_accounts_telegram_chat_id"), table_name="channel_accounts")
    op.drop_index(op.f("ix_channel_accounts_telegram_user_id"), table_name="channel_accounts")
    op.drop_index(
        op.f("ix_channel_accounts_telegram_business_connection_id"), table_name="channel_accounts"
    )
    op.drop_index(op.f("ix_channel_accounts_connection_mode"), table_name="channel_accounts")
    op.drop_column("channel_accounts", "telegram_business_enabled")
    op.drop_column("channel_accounts", "telegram_last_sync_at")
    op.drop_column("channel_accounts", "telegram_capabilities_json")
    op.drop_column("channel_accounts", "telegram_rights_json")
    op.drop_column("channel_accounts", "telegram_chat_id")
    op.drop_column("channel_accounts", "telegram_username")
    op.drop_column("channel_accounts", "telegram_user_id")
    op.drop_column("channel_accounts", "telegram_business_connection_id")
    op.drop_column("channel_accounts", "connection_mode")

    op.execute("DROP TYPE conversation_response_mode")
    op.execute("DROP TYPE telegram_connection_session_status")
    op.execute("DROP TYPE telegram_connection_mode")
