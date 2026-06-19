"""channel connection sessions for OAuth flows

Revision ID: 20260619_0031
Revises: 20260618_0030
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260619_0031"
down_revision: str | None = "20260618_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

channel_connection_provider = postgresql.ENUM(
    "instagram", name="channel_connection_provider", create_type=False
)
channel_connection_method = postgresql.ENUM(
    "meta_oauth_business_login", name="channel_connection_method", create_type=False
)
channel_connection_session_status = postgresql.ENUM(
    "pending",
    "redirected",
    "authorized",
    "account_selection_required",
    "connected",
    "failed",
    "expired",
    "cancelled",
    name="channel_connection_session_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE TYPE channel_connection_provider AS ENUM ('instagram')")
    op.execute(
        "CREATE TYPE channel_connection_method AS ENUM ('meta_oauth_business_login')"
    )
    op.execute(
        "CREATE TYPE channel_connection_session_status AS ENUM ("
        "'pending', 'redirected', 'authorized', 'account_selection_required', "
        "'connected', 'failed', 'expired', 'cancelled')"
    )

    op.create_table(
        "channel_connection_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", channel_connection_provider, nullable=False),
        sa.Column("method", channel_connection_method, nullable=False),
        sa.Column("status", channel_connection_session_status, nullable=False, server_default="pending"),
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("nonce", sa.String(length=128), nullable=False),
        sa.Column("code_verifier", sa.String(length=255), nullable=True),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column(
            "requested_scopes_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "provider_payload_redacted",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("oauth_token_encrypted", sa.Text(), nullable=True),
        sa.Column("selected_external_account_id", sa.String(length=128), nullable=True),
        sa.Column("selected_page_id", sa.String(length=128), nullable=True),
        sa.Column("selected_instagram_business_account_id", sa.String(length=128), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state", name="uq_channel_connection_sessions_state"),
    )
    op.create_index(
        op.f("ix_channel_connection_sessions_shop_id"),
        "channel_connection_sessions",
        ["shop_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_connection_sessions_provider"),
        "channel_connection_sessions",
        ["provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_connection_sessions_status"),
        "channel_connection_sessions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_connection_sessions_state"),
        "channel_connection_sessions",
        ["state"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_connection_sessions_created_by"),
        "channel_connection_sessions",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_connection_sessions_expires_at"),
        "channel_connection_sessions",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_channel_connection_sessions_shop_status",
        "channel_connection_sessions",
        ["shop_id", "status"],
        unique=False,
    )

    op.execute(
        """
        CREATE UNIQUE INDEX uq_channel_accounts_provider_webhook_verify_token
        ON channel_accounts (provider, webhook_verify_token)
        WHERE webhook_verify_token IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_channel_accounts_provider_webhook_verify_token")
    op.drop_index("ix_channel_connection_sessions_shop_status", table_name="channel_connection_sessions")
    op.drop_index(
        op.f("ix_channel_connection_sessions_expires_at"),
        table_name="channel_connection_sessions",
    )
    op.drop_index(
        op.f("ix_channel_connection_sessions_created_by"),
        table_name="channel_connection_sessions",
    )
    op.drop_index(
        op.f("ix_channel_connection_sessions_state"),
        table_name="channel_connection_sessions",
    )
    op.drop_index(
        op.f("ix_channel_connection_sessions_status"),
        table_name="channel_connection_sessions",
    )
    op.drop_index(
        op.f("ix_channel_connection_sessions_provider"),
        table_name="channel_connection_sessions",
    )
    op.drop_index(
        op.f("ix_channel_connection_sessions_shop_id"),
        table_name="channel_connection_sessions",
    )
    op.drop_table("channel_connection_sessions")
    op.execute("DROP TYPE channel_connection_session_status")
    op.execute("DROP TYPE channel_connection_method")
    op.execute("DROP TYPE channel_connection_provider")
