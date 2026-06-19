"""telegram managed bot support

Revision ID: 20260619_0033
Revises: 20260619_0032
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260619_0033"
down_revision: str | None = "20260619_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE telegram_connection_session_status "
        "ADD VALUE IF NOT EXISTS 'waiting_managed_bot_approval'"
    )
    op.add_column(
        "channel_accounts",
        sa.Column(
            "managed_bot",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "channel_accounts",
        sa.Column("manager_bot_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "channel_accounts",
        sa.Column("managed_bot_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        op.f("ix_channel_accounts_managed_bot_id"),
        "channel_accounts",
        ["managed_bot_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_channel_accounts_managed_bot_id"), table_name="channel_accounts")
    op.drop_column("channel_accounts", "managed_bot_id")
    op.drop_column("channel_accounts", "manager_bot_id")
    op.drop_column("channel_accounts", "managed_bot")
