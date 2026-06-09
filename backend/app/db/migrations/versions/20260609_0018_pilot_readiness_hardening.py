"""pilot readiness hardening

Revision ID: 20260609_0018
Revises: 20260609_0017
Create Date: 2026-06-09 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260609_0018"
down_revision: str | None = "20260609_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

pilot_event_severity = postgresql.ENUM("info", "warning", "error", "critical", name="pilot_event_severity", create_type=False)


def upgrade() -> None:
    op.execute("CREATE TYPE pilot_event_severity AS ENUM ('info', 'warning', 'error', 'critical')")
    op.create_table(
        "pilot_settings",
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pilot_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("pilot_name", sa.String(length=255), nullable=False, server_default="Pilot"),
        sa.Column("pilot_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pilot_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_auto_sent_messages_per_day", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("max_auto_created_orders_per_day", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("require_operator_approval_for_first_50_orders", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allowed_instagram_account_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("allowed_product_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("emergency_stop_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("shop_id"),
    )
    op.create_index(op.f("ix_pilot_settings_pilot_enabled"), "pilot_settings", ["pilot_enabled"], unique=False)
    op.create_index(op.f("ix_pilot_settings_emergency_stop_enabled"), "pilot_settings", ["emergency_stop_enabled"], unique=False)

    op.create_table(
        "pilot_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("severity", pilot_event_severity, nullable=False, server_default="info"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pilot_events_shop_id"), "pilot_events", ["shop_id"], unique=False)
    op.create_index(op.f("ix_pilot_events_event_type"), "pilot_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_pilot_events_severity"), "pilot_events", ["severity"], unique=False)
    op.create_index(op.f("ix_pilot_events_created_at"), "pilot_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pilot_events_created_at"), table_name="pilot_events")
    op.drop_index(op.f("ix_pilot_events_severity"), table_name="pilot_events")
    op.drop_index(op.f("ix_pilot_events_event_type"), table_name="pilot_events")
    op.drop_index(op.f("ix_pilot_events_shop_id"), table_name="pilot_events")
    op.drop_table("pilot_events")
    op.drop_index(op.f("ix_pilot_settings_emergency_stop_enabled"), table_name="pilot_settings")
    op.drop_index(op.f("ix_pilot_settings_pilot_enabled"), table_name="pilot_settings")
    op.drop_table("pilot_settings")
    op.execute("DROP TYPE pilot_event_severity")
