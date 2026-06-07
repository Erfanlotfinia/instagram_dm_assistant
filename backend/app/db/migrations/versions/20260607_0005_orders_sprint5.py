"""Sprint 5 orders, payments, shipments

Revision ID: 20260607_0005
Revises: 20260607_0004
Create Date: 2026-06-07 18:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260607_0005"
down_revision: str | None = "20260607_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

order_status = postgresql.ENUM(
    "draft",
    "waiting_for_confirmation",
    "confirmed",
    "waiting_for_payment",
    "paid",
    "preparing",
    "shipped",
    "completed",
    "cancelled",
    "expired",
    name="order_status",
    create_type=False,
)
order_payment_status = postgresql.ENUM(
    "unpaid",
    "pending",
    "paid",
    "failed",
    "refunded",
    name="order_payment_status",
    create_type=False,
)
order_shipping_status = postgresql.ENUM(
    "not_started",
    "preparing",
    "shipped",
    "delivered",
    name="order_shipping_status",
    create_type=False,
)
payment_provider = postgresql.ENUM(
    "manual",
    "zarinpal",
    "nextpay",
    "idpay",
    "mock",
    name="payment_provider",
    create_type=False,
)
payment_record_status = postgresql.ENUM(
    "created",
    "pending",
    "paid",
    "failed",
    "cancelled",
    name="payment_record_status",
    create_type=False,
)
shipment_provider = postgresql.ENUM(
    "manual",
    "post",
    "tipax",
    "chapar",
    "other",
    name="shipment_provider",
    create_type=False,
)
shipment_status = postgresql.ENUM(
    "pending",
    "preparing",
    "shipped",
    "delivered",
    "failed",
    name="shipment_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    order_status.create(bind, checkfirst=True)
    order_payment_status.create(bind, checkfirst=True)
    order_shipping_status.create(bind, checkfirst=True)
    payment_provider.create(bind, checkfirst=True)
    payment_record_status.create(bind, checkfirst=True)
    shipment_provider.create(bind, checkfirst=True)
    shipment_status.create(bind, checkfirst=True)

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", order_status, nullable=False, server_default="draft"),
        sa.Column("subtotal_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("shipping_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("payment_status", order_payment_status, nullable=False, server_default="unpaid"),
        sa.Column("shipping_status", order_shipping_status, nullable=False, server_default="not_started"),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("city", sa.String(length=128), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("postal_code", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_shop_id"), "orders", ["shop_id"], unique=False)
    op.create_index(op.f("ix_orders_customer_id"), "orders", ["customer_id"], unique=False)
    op.create_index(op.f("ix_orders_conversation_id"), "orders", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)
    op.create_index(op.f("ix_orders_payment_status"), "orders", ["payment_status"], unique=False)
    op.create_index(op.f("ix_orders_shipping_status"), "orders", ["shipping_status"], unique=False)
    op.create_index(op.f("ix_orders_expires_at"), "orders", ["expires_at"], unique=False)
    op.create_index(op.f("ix_orders_created_at"), "orders", ["created_at"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_title_snapshot", sa.String(length=255), nullable=False),
        sa.Column("variant_color_snapshot", sa.String(length=64), nullable=True),
        sa.Column("variant_size_snapshot", sa.String(length=64), nullable=True),
        sa.Column("sku_snapshot", sa.String(length=128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_variant_id"], ["product_variants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_items_product_id"), "order_items", ["product_id"], unique=False)
    op.create_index(
        op.f("ix_order_items_product_variant_id"), "order_items", ["product_variant_id"], unique=False
    )

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", payment_provider, nullable=False),
        sa.Column("status", payment_record_status, nullable=False, server_default="created"),
        sa.Column("payment_url", sa.String(length=2048), nullable=True),
        sa.Column("provider_reference", sa.String(length=255), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_order_id"), "payments", ["order_id"], unique=False)
    op.create_index(op.f("ix_payments_status"), "payments", ["status"], unique=False)
    op.create_index(op.f("ix_payments_provider_reference"), "payments", ["provider_reference"], unique=False)
    op.create_index(op.f("ix_payments_created_at"), "payments", ["created_at"], unique=False)

    op.create_table(
        "shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", shipment_provider, nullable=False, server_default="manual"),
        sa.Column("status", shipment_status, nullable=False, server_default="pending"),
        sa.Column("tracking_code", sa.String(length=128), nullable=True),
        sa.Column("tracking_url", sa.String(length=2048), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shipments_order_id"), "shipments", ["order_id"], unique=False)
    op.create_index(op.f("ix_shipments_status"), "shipments", ["status"], unique=False)
    op.create_index(op.f("ix_shipments_tracking_code"), "shipments", ["tracking_code"], unique=False)
    op.create_index(op.f("ix_shipments_created_at"), "shipments", ["created_at"], unique=False)

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admin_audit_logs_shop_id"), "admin_audit_logs", ["shop_id"], unique=False)
    op.create_index(op.f("ix_admin_audit_logs_user_id"), "admin_audit_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_admin_audit_logs_action"), "admin_audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_admin_audit_logs_entity_type"), "admin_audit_logs", ["entity_type"], unique=False)
    op.create_index(op.f("ix_admin_audit_logs_entity_id"), "admin_audit_logs", ["entity_id"], unique=False)
    op.create_index(op.f("ix_admin_audit_logs_created_at"), "admin_audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_audit_logs_created_at"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_entity_id"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_entity_type"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_action"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_user_id"), table_name="admin_audit_logs")
    op.drop_index(op.f("ix_admin_audit_logs_shop_id"), table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")

    op.drop_index(op.f("ix_shipments_created_at"), table_name="shipments")
    op.drop_index(op.f("ix_shipments_tracking_code"), table_name="shipments")
    op.drop_index(op.f("ix_shipments_status"), table_name="shipments")
    op.drop_index(op.f("ix_shipments_order_id"), table_name="shipments")
    op.drop_table("shipments")

    op.drop_index(op.f("ix_payments_created_at"), table_name="payments")
    op.drop_index(op.f("ix_payments_provider_reference"), table_name="payments")
    op.drop_index(op.f("ix_payments_status"), table_name="payments")
    op.drop_index(op.f("ix_payments_order_id"), table_name="payments")
    op.drop_table("payments")

    op.drop_index(op.f("ix_order_items_product_variant_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_product_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_table("order_items")

    op.drop_index(op.f("ix_orders_created_at"), table_name="orders")
    op.drop_index(op.f("ix_orders_expires_at"), table_name="orders")
    op.drop_index(op.f("ix_orders_shipping_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_payment_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_conversation_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_customer_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_shop_id"), table_name="orders")
    op.drop_table("orders")

    shipment_status.drop(op.get_bind(), checkfirst=True)
    shipment_provider.drop(op.get_bind(), checkfirst=True)
    payment_record_status.drop(op.get_bind(), checkfirst=True)
    payment_provider.drop(op.get_bind(), checkfirst=True)
    order_shipping_status.drop(op.get_bind(), checkfirst=True)
    order_payment_status.drop(op.get_bind(), checkfirst=True)
    order_status.drop(op.get_bind(), checkfirst=True)
