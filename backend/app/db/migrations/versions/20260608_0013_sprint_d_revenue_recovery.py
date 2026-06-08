"""Sprint D abandoned recovery, customer preferences, upsells, analytics

Revision ID: 20260608_0013
Revises: 20260608_0012
Create Date: 2026-06-08 18:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260608_0013"
down_revision: str | None = "20260608_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        order_recovery_status = postgresql.ENUM(
            "none", "eligible", "in_progress", "recovered", "failed", "stopped",
            name="order_recovery_status",
            create_type=False,
        )
        order_recovery_attempt_status = postgresql.ENUM(
            "created", "sent", "skipped", "failed",
            name="order_recovery_attempt_status",
            create_type=False,
        )
        upsell_suggestion_status = postgresql.ENUM(
            "suggested", "accepted", "rejected", "skipped",
            name="upsell_suggestion_status",
            create_type=False,
        )
        order_recovery_status.create(bind, checkfirst=True)
        order_recovery_attempt_status.create(bind, checkfirst=True)
        upsell_suggestion_status.create(bind, checkfirst=True)
    else:
        order_recovery_status = sa.Enum(
            "none", "eligible", "in_progress", "recovered", "failed", "stopped",
            name="order_recovery_status",
        )
        order_recovery_attempt_status = sa.Enum(
            "created", "sent", "skipped", "failed",
            name="order_recovery_attempt_status",
        )
        upsell_suggestion_status = sa.Enum(
            "suggested", "accepted", "rejected", "skipped",
            name="upsell_suggestion_status",
        )

    op.add_column(
        "orders",
        sa.Column(
            "recovery_status",
            order_recovery_status,
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column(
        "orders",
        sa.Column("recovery_attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "orders",
        sa.Column("last_recovery_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_orders_recovery_status", "orders", ["recovery_status"])

    op.create_table(
        "abandoned_order_recovery_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("trigger_after_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("message_template", sa.Text(), nullable=False),
        sa.Column(
            "only_inside_allowed_messaging_window",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_abandoned_order_recovery_rules_shop_id",
        "abandoned_order_recovery_rules",
        ["shop_id"],
    )

    op.create_table(
        "order_recovery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("status", order_recovery_attempt_status, nullable=False, server_default="created"),
        sa.Column("skip_reason", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_recovery_attempts_order_id", "order_recovery_attempts", ["order_id"])
    op.create_index(
        "ix_order_recovery_attempts_conversation_id",
        "order_recovery_attempts",
        ["conversation_id"],
    )

    op.create_table(
        "customer_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preferred_size", sa.String(length=64), nullable=True),
        sa.Column("preferred_colors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("preferred_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_successful_size", sa.String(length=64), nullable=True),
        sa.Column("last_successful_city", sa.String(length=128), nullable=True),
        sa.Column("last_successful_address_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id"),
    )
    op.create_index("ix_customer_preferences_customer_id", "customer_preferences", ["customer_id"])

    op.create_table(
        "product_upsells",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_template", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id", "source_product_id", "target_product_id",
            name="uq_product_upsells_shop_source_target",
        ),
    )
    op.create_index("ix_product_upsells_shop_id", "product_upsells", ["shop_id"])

    op.create_table(
        "upsell_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suggested_text", sa.Text(), nullable=False),
        sa.Column("status", upsell_suggestion_status, nullable=False, server_default="suggested"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_upsell_suggestions_shop_id", "upsell_suggestions", ["shop_id"])
    op.create_index("ix_upsell_suggestions_conversation_id", "upsell_suggestions", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_upsell_suggestions_conversation_id", table_name="upsell_suggestions")
    op.drop_index("ix_upsell_suggestions_shop_id", table_name="upsell_suggestions")
    op.drop_table("upsell_suggestions")
    op.drop_index("ix_product_upsells_shop_id", table_name="product_upsells")
    op.drop_table("product_upsells")
    op.drop_index("ix_customer_preferences_customer_id", table_name="customer_preferences")
    op.drop_table("customer_preferences")
    op.drop_index("ix_order_recovery_attempts_conversation_id", table_name="order_recovery_attempts")
    op.drop_index("ix_order_recovery_attempts_order_id", table_name="order_recovery_attempts")
    op.drop_table("order_recovery_attempts")
    op.drop_index("ix_abandoned_order_recovery_rules_shop_id", table_name="abandoned_order_recovery_rules")
    op.drop_table("abandoned_order_recovery_rules")
    op.drop_index("ix_orders_recovery_status", table_name="orders")
    op.drop_column("orders", "last_recovery_at")
    op.drop_column("orders", "recovery_attempt_count")
    op.drop_column("orders", "recovery_status")
