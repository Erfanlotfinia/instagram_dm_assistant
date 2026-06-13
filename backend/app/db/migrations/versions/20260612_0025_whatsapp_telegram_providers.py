"""whatsapp and telegram provider hardening

Revision ID: 20260612_0025
Revises: 20260612_0024
Create Date: 2026-06-12 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260612_0025"
down_revision: str | None = "20260612_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

whatsapp_template_category = postgresql.ENUM(
    "marketing",
    "utility",
    "authentication",
    "service",
    "unknown",
    name="whatsapp_template_category",
    create_type=False,
)
whatsapp_template_status = postgresql.ENUM(
    "draft",
    "submitted",
    "approved",
    "rejected",
    "paused",
    "disabled",
    "unknown",
    name="whatsapp_template_status",
    create_type=False,
)
channel_provider = postgresql.ENUM(
    "instagram",
    "whatsapp",
    "telegram",
    "bale",
    "rubika",
    name="channel_provider",
    create_type=False,
)


def upgrade() -> None:
    whatsapp_template_category.create(op.get_bind(), checkfirst=True)
    whatsapp_template_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "channel_delivery_status_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", channel_provider, nullable=False),
        sa.Column("channel_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_message_id", sa.String(length=128), nullable=False),
        sa.Column("external_chat_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column(
            "raw_payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["channel_account_id"], ["channel_accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "channel_account_id",
            "external_message_id",
            "status",
            name="uq_channel_delivery_status_event",
        ),
    )
    for col in [
        "shop_id",
        "provider",
        "channel_account_id",
        "external_message_id",
        "external_chat_id",
        "status",
        "occurred_at",
        "created_at",
    ]:
        op.create_index(
            op.f(f"ix_channel_delivery_status_events_{col}"),
            "channel_delivery_status_events",
            [col],
            unique=False,
        )

    op.create_table(
        "whatsapp_message_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_name", sa.String(length=255), nullable=False),
        sa.Column(
            "language_code",
            sa.String(length=16),
            nullable=False,
            server_default="en_US",
        ),
        sa.Column(
            "category",
            whatsapp_template_category,
            nullable=False,
            server_default="unknown",
        ),
        sa.Column(
            "status", whatsapp_template_status, nullable=False, server_default="draft"
        ),
        sa.Column(
            "components_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("external_template_id", sa.String(length=128), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["channel_account_id"], ["channel_accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id",
            "channel_account_id",
            "template_name",
            "language_code",
            name="uq_whatsapp_template_name_language",
        ),
    )
    for col in [
        "shop_id",
        "channel_account_id",
        "template_name",
        "language_code",
        "category",
        "status",
        "external_template_id",
        "created_at",
        "updated_at",
    ]:
        op.create_index(
            op.f(f"ix_whatsapp_message_templates_{col}"),
            "whatsapp_message_templates",
            [col],
            unique=False,
        )


def downgrade() -> None:
    op.drop_table("whatsapp_message_templates")
    op.drop_table("channel_delivery_status_events")
    whatsapp_template_status.drop(op.get_bind(), checkfirst=True)
    whatsapp_template_category.drop(op.get_bind(), checkfirst=True)
