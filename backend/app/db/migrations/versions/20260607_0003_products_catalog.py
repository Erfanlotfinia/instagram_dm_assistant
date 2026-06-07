"""Sprint 3 product catalog, variants, inventory, and Instagram product maps

Revision ID: 20260607_0003
Revises: 20260607_0002
Create Date: 2026-06-07 18:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260607_0003"
down_revision: str | None = "20260607_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

product_status = postgresql.ENUM("active", "inactive", "archived", name="product_status", create_type=False)
inventory_movement_type = postgresql.ENUM(
    "reserve", "release", "sale", "adjustment", name="inventory_movement_type", create_type=False
)
confidence_source = postgresql.ENUM(
    "manual",
    "caption_match",
    "image_match",
    "admin_confirmed",
    name="confidence_source",
    create_type=False,
)


def upgrade() -> None:
    product_status.create(op.get_bind(), checkfirst=True)
    inventory_movement_type.create(op.get_bind(), checkfirst=True)
    confidence_source.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", product_status, nullable=False),
        sa.Column("base_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("main_image_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_shop_id"), "products", ["shop_id"], unique=False)

    op.create_table(
        "product_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("color", sa.String(length=64), nullable=True),
        sa.Column("size", sa.String(length=64), nullable=True),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False),
        sa.Column("reserved_quantity", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "sku", name="uq_product_variants_product_sku"),
    )
    op.create_index(op.f("ix_product_variants_product_id"), "product_variants", ["product_id"], unique=False)
    op.create_index(op.f("ix_product_variants_sku"), "product_variants", ["sku"], unique=False)

    op.create_table(
        "instagram_product_maps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instagram_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instagram_media_id", sa.String(length=128), nullable=True),
        sa.Column("instagram_post_url", sa.String(length=2048), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("confidence_source", confidence_source, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["instagram_account_id"], ["instagram_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_instagram_product_maps_shop_id"), "instagram_product_maps", ["shop_id"], unique=False)
    op.create_index(
        op.f("ix_instagram_product_maps_instagram_account_id"),
        "instagram_product_maps",
        ["instagram_account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_instagram_product_maps_instagram_media_id"),
        "instagram_product_maps",
        ["instagram_media_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_instagram_product_maps_instagram_post_url"),
        "instagram_product_maps",
        ["instagram_post_url"],
        unique=False,
    )
    op.create_index(
        op.f("ix_instagram_product_maps_product_id"), "instagram_product_maps", ["product_id"], unique=False
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_type", inventory_movement_type, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column("reference_type", sa.String(length=64), nullable=True),
        sa.Column("reference_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_inventory_movements_product_variant_id"),
        "inventory_movements",
        ["product_variant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_movements_created_at"), "inventory_movements", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_inventory_movements_created_at"), table_name="inventory_movements")
    op.drop_index(op.f("ix_inventory_movements_product_variant_id"), table_name="inventory_movements")
    op.drop_table("inventory_movements")

    op.drop_index(op.f("ix_instagram_product_maps_product_id"), table_name="instagram_product_maps")
    op.drop_index(op.f("ix_instagram_product_maps_instagram_post_url"), table_name="instagram_product_maps")
    op.drop_index(op.f("ix_instagram_product_maps_instagram_media_id"), table_name="instagram_product_maps")
    op.drop_index(op.f("ix_instagram_product_maps_instagram_account_id"), table_name="instagram_product_maps")
    op.drop_index(op.f("ix_instagram_product_maps_shop_id"), table_name="instagram_product_maps")
    op.drop_table("instagram_product_maps")

    op.drop_index(op.f("ix_product_variants_sku"), table_name="product_variants")
    op.drop_index(op.f("ix_product_variants_product_id"), table_name="product_variants")
    op.drop_table("product_variants")

    op.drop_index(op.f("ix_products_shop_id"), table_name="products")
    op.drop_table("products")

    confidence_source.drop(op.get_bind(), checkfirst=True)
    inventory_movement_type.drop(op.get_bind(), checkfirst=True)
    product_status.drop(op.get_bind(), checkfirst=True)
