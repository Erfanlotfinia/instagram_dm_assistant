"""Audit remediation: outbox, order payment hardening, TRL validation mode

Revision ID: 20260610_0023
Revises: 20260609_0022
Create Date: 2026-06-10 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260610_0023"
down_revision: str | None = "20260609_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

outbox_event_status = postgresql.ENUM(
    "pending", "published", "failed", name="outbox_event_status", create_type=False
)


def upgrade() -> None:
    op.execute("CREATE TYPE outbox_event_status AS ENUM ('pending', 'published', 'failed')")

    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=True),
        sa.Column("aggregate_id", sa.String(length=128), nullable=True),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", outbox_event_status, nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outbox_events_event_type"), "outbox_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_outbox_events_shop_id"), "outbox_events", ["shop_id"], unique=False)
    op.create_index(op.f("ix_outbox_events_status"), "outbox_events", ["status"], unique=False)
    op.create_index(op.f("ix_outbox_events_next_attempt_at"), "outbox_events", ["next_attempt_at"], unique=False)
    op.create_index(op.f("ix_outbox_events_created_at"), "outbox_events", ["created_at"], unique=False)

    op.add_column("orders", sa.Column("admin_override_reason", sa.String(length=512), nullable=True))
    op.add_column("orders", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "orders",
        sa.Column("payment_confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("orders", sa.Column("inventory_finalized_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_orders_payment_confirmed_by_users",
        "orders",
        "users",
        ["payment_confirmed_by"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "inventory_reservations",
        sa.Column("idempotency_key", sa.String(length=256), nullable=True),
    )

    op.add_column(
        "trl_validation_runs",
        sa.Column(
            "validation_mode",
            sa.String(length=64),
            nullable=False,
            server_default="deterministic_regression",
        ),
    )
    op.create_index(
        op.f("ix_trl_validation_runs_validation_mode"),
        "trl_validation_runs",
        ["validation_mode"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_trl_validation_runs_validation_mode"), table_name="trl_validation_runs")
    op.drop_column("trl_validation_runs", "validation_mode")
    op.drop_column("inventory_reservations", "idempotency_key")
    op.drop_constraint("fk_orders_payment_confirmed_by_users", "orders", type_="foreignkey")
    op.drop_column("orders", "inventory_finalized_at")
    op.drop_column("orders", "payment_confirmed_by")
    op.drop_column("orders", "paid_at")
    op.drop_column("orders", "admin_override_reason")
    op.drop_table("outbox_events")
    op.execute("DROP TYPE outbox_event_status")
