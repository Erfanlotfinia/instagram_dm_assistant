"""order correctness foundation

Revision ID: 20260609_0019
Revises: 20260609_0018
Create Date: 2026-06-09 18:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260609_0019"
down_revision: str | None = "20260609_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_ORDER_STATUSES = (
    "draft",
    "waiting_for_clarification",
    "ready_for_confirmation",
    "reserved",
    "payment_pending",
    "paid",
    "order_created",
    "failed",
    "cancelled",
    "expired",
)

inventory_reservation_status = postgresql.ENUM(
    "active", "confirmed", "released", "expired", name="inventory_reservation_status", create_type=False
)
order_transition_trigger = postgresql.ENUM(
    "api", "webhook", "worker", "system", name="order_transition_trigger", create_type=False
)
order_correctness_action = postgresql.ENUM(
    "create_draft",
    "clarify",
    "confirm",
    "reserve",
    "payment_link",
    "complete",
    "cancel",
    "mark_paid",
    "expire",
    name="order_correctness_action",
    create_type=False,
)
webhook_dedupe_outcome = postgresql.ENUM(
    "processed", "duplicate", "ignored", name="webhook_dedupe_outcome", create_type=False
)
operator_review_decision = postgresql.ENUM(
    "approved", "rejected", name="operator_review_decision", create_type=False
)


def _create_enum_if_not_exists(name: str, values: str) -> None:
    op.execute(
        f"""
        DO $$ BEGIN
            CREATE TYPE {name} AS ENUM ({values});
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )


def _migrate_order_status_enum() -> None:
    """Replace order_status enum; drop column default first (PG keeps default on old type)."""
    op.execute("ALTER TABLE orders ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE VARCHAR(64) USING status::text")
    op.execute(
        """
        UPDATE orders SET status = CASE status
            WHEN 'waiting_for_confirmation' THEN 'ready_for_confirmation'
            WHEN 'confirmed' THEN 'ready_for_confirmation'
            WHEN 'waiting_for_payment' THEN 'payment_pending'
            WHEN 'preparing' THEN 'paid'
            WHEN 'shipped' THEN 'order_created'
            WHEN 'completed' THEN 'order_created'
            ELSE status
        END
        """
    )
    op.execute("DROP TYPE IF EXISTS order_status_old")
    op.execute(
        """
        DO $$ BEGIN
            ALTER TYPE order_status RENAME TO order_status_old;
        EXCEPTION
            WHEN undefined_object THEN NULL;
        END $$;
        """
    )
    op.execute("DROP TYPE IF EXISTS order_status")
    op.execute(
        f"CREATE TYPE order_status AS ENUM ({', '.join(repr(s) for s in NEW_ORDER_STATUSES)})"
    )
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE order_status USING status::order_status")
    op.execute("DROP TYPE IF EXISTS order_status_old")
    op.execute("ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'draft'::order_status")


def upgrade() -> None:
    _create_enum_if_not_exists(
        "inventory_reservation_status",
        "'active', 'confirmed', 'released', 'expired'",
    )
    _create_enum_if_not_exists("order_transition_trigger", "'api', 'webhook', 'worker', 'system'")
    _create_enum_if_not_exists(
        "order_correctness_action",
        "'create_draft', 'clarify', 'confirm', 'reserve', 'payment_link', "
        "'complete', 'cancel', 'mark_paid', 'expire'",
    )
    _create_enum_if_not_exists("webhook_dedupe_outcome", "'processed', 'duplicate', 'ignored'")
    _create_enum_if_not_exists("operator_review_decision", "'approved', 'rejected'")

    _migrate_order_status_enum()

    op.add_column("orders", sa.Column("customer_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("customer_confirmation_source", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True))
    op.add_column(
        "orders",
        sa.Column(
            "confidence_source",
            sa.Enum("manual", "caption_match", "image_match", "admin_confirmed", name="confidence_source", create_type=False),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column("pilot_mode_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("orders", sa.Column("idempotency_key", sa.String(length=256), nullable=True))
    op.create_index("ix_orders_shop_idempotency_key", "orders", ["shop_id", "idempotency_key"], unique=True)

    op.create_table(
        "inventory_reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            inventory_reservation_status,
            nullable=False,
            server_default="active",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_reservations_shop_id", "inventory_reservations", ["shop_id"])
    op.create_index("ix_inventory_reservations_order_id", "inventory_reservations", ["order_id"])
    op.create_index("ix_inventory_reservations_expires_at", "inventory_reservations", ["expires_at"])
    op.create_index(
        "uq_inventory_reservations_active_order_variant",
        "inventory_reservations",
        ["order_id", "product_variant_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.add_column(
        "orders",
        sa.Column("active_reservation_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_orders_active_reservation_id",
        "orders",
        "inventory_reservations",
        ["active_reservation_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "order_items_draft",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("product_title_snapshot", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("variant_label_snapshot", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_variant_id"], ["product_variants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_draft_shop_order", "order_items_draft", ["shop_id", "order_id"])

    op.create_table(
        "order_state_transitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(length=64), nullable=False),
        sa.Column("to_status", sa.String(length=64), nullable=False),
        sa.Column("trigger", order_transition_trigger, nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_order_state_transitions_shop_order_created",
        "order_state_transitions",
        ["shop_id", "order_id", "created_at"],
    )

    op.create_table(
        "action_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", order_correctness_action, nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("denial_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("policy_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_attempts_shop_order", "action_attempts", ["shop_id", "order_id"])

    op.create_table(
        "pilot_modes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", order_correctness_action, nullable=False),
        sa.Column("permitted", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("confidence_threshold", sa.Numeric(5, 4), nullable=False, server_default="0.6"),
        sa.Column("require_customer_confirmation", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "action", name="uq_pilot_modes_shop_action"),
    )
    op.create_index("ix_pilot_modes_shop_id", "pilot_modes", ["shop_id"])

    op.create_table(
        "operator_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", operator_review_decision, nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operator_reviews_shop_order", "operator_reviews", ["shop_id", "order_id"])

    op.add_column("webhook_events", sa.Column("idempotency_key", sa.String(length=256), nullable=True))
    op.add_column("webhook_events", sa.Column("trace_id", sa.String(length=128), nullable=True))
    op.add_column(
        "webhook_events",
        sa.Column("dedupe_outcome", webhook_dedupe_outcome, nullable=True),
    )
    op.create_index(
        "uq_webhook_events_provider_idempotency",
        "webhook_events",
        ["provider", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_index(
        "uq_inventory_movements_reservation_ref",
        "inventory_movements",
        ["reference_type", "reference_id", "movement_type", "product_variant_id"],
        unique=True,
        postgresql_where=sa.text("reference_type = 'reservation'"),
    )

    # Seed default pilot_modes for existing shops
    op.execute(
        """
        INSERT INTO pilot_modes (id, shop_id, action, permitted, confidence_threshold, require_customer_confirmation)
        SELECT gen_random_uuid(), s.id, a.action::order_correctness_action, true, 0.6, false
        FROM shops s
        CROSS JOIN (
            SELECT unnest(ARRAY[
                'create_draft', 'clarify', 'confirm', 'reserve', 'payment_link',
                'complete', 'cancel', 'mark_paid', 'expire'
            ]) AS action
        ) a
        ON CONFLICT (shop_id, action) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("uq_inventory_movements_reservation_ref", table_name="inventory_movements")
    op.drop_index("uq_webhook_events_provider_idempotency", table_name="webhook_events")
    op.drop_column("webhook_events", "dedupe_outcome")
    op.drop_column("webhook_events", "trace_id")
    op.drop_column("webhook_events", "idempotency_key")

    op.drop_table("operator_reviews")
    op.drop_table("pilot_modes")
    op.drop_table("action_attempts")
    op.drop_table("order_state_transitions")
    op.drop_table("order_items_draft")

    op.drop_constraint("fk_orders_active_reservation_id", "orders", type_="foreignkey")
    op.drop_column("orders", "active_reservation_id")
    op.drop_table("inventory_reservations")

    op.drop_index("ix_orders_shop_idempotency_key", table_name="orders")
    op.drop_column("orders", "idempotency_key")
    op.drop_column("orders", "pilot_mode_snapshot")
    op.drop_column("orders", "confidence_source")
    op.drop_column("orders", "confidence_score")
    op.drop_column("orders", "customer_confirmation_source")
    op.drop_column("orders", "customer_confirmed_at")

    op.execute("ALTER TABLE orders ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE VARCHAR(64) USING status::text")
    op.execute(
        """
        UPDATE orders SET status = CASE status
            WHEN 'ready_for_confirmation' THEN 'waiting_for_confirmation'
            WHEN 'payment_pending' THEN 'waiting_for_payment'
            WHEN 'order_created' THEN 'completed'
            WHEN 'waiting_for_clarification' THEN 'draft'
            WHEN 'reserved' THEN 'waiting_for_confirmation'
            WHEN 'failed' THEN 'cancelled'
            ELSE status
        END
        """
    )
    op.execute("DROP TYPE IF EXISTS order_status_old")
    op.execute("ALTER TYPE order_status RENAME TO order_status_old")
    op.execute(
        "CREATE TYPE order_status AS ENUM ("
        "'draft', 'waiting_for_confirmation', 'confirmed', 'waiting_for_payment', "
        "'paid', 'preparing', 'shipped', 'completed', 'cancelled', 'expired')"
    )
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE order_status USING status::order_status")
    op.execute("DROP TYPE order_status_old")
    op.execute("ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'draft'::order_status")

    op.execute("DROP TYPE operator_review_decision")
    op.execute("DROP TYPE webhook_dedupe_outcome")
    op.execute("DROP TYPE order_correctness_action")
    op.execute("DROP TYPE order_transition_trigger")
    op.execute("DROP TYPE inventory_reservation_status")
