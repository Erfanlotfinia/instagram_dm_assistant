"""Sprint 2 webhook events and message idempotency

Revision ID: 20260607_0002
Revises: 20260607_0001
Create Date: 2026-06-07 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260607_0002"
down_revision: str | None = "20260607_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

webhook_provider = postgresql.ENUM("instagram", name="webhook_provider", create_type=False)
webhook_processing_status = postgresql.ENUM(
    "received", "queued", "processed", "failed", name="webhook_processing_status", create_type=False
)


def upgrade() -> None:
    webhook_provider.create(op.get_bind(), checkfirst=True)
    webhook_processing_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", webhook_provider, nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("instagram_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("processing_status", webhook_processing_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["instagram_account_id"], ["instagram_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhook_events_created_at"), "webhook_events", ["created_at"], unique=False)
    op.create_index(
        op.f("ix_webhook_events_instagram_account_id"), "webhook_events", ["instagram_account_id"], unique=False
    )
    op.create_index(op.f("ix_webhook_events_shop_id"), "webhook_events", ["shop_id"], unique=False)

    op.create_unique_constraint("uq_messages_instagram_message_id", "messages", ["instagram_message_id"])


def downgrade() -> None:
    op.drop_constraint("uq_messages_instagram_message_id", "messages", type_="unique")
    op.drop_index(op.f("ix_webhook_events_shop_id"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_instagram_account_id"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_created_at"), table_name="webhook_events")
    op.drop_table("webhook_events")
    webhook_processing_status.drop(op.get_bind(), checkfirst=True)
    webhook_provider.drop(op.get_bind(), checkfirst=True)
