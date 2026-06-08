"""sprint a fashion order hardening

Revision ID: 20260607_0010
Revises: 20260607_0009
Create Date: 2026-06-07
"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260607_0010"
down_revision = "20260607_0009"
branch_labels = None
depends_on = None

COLOR_DEFAULTS = [
    ("مشکی", "black", "fa"), ("سیاه", "black", "fa"), ("black", "black", "en"),
    ("سفید", "white", "fa"), ("white", "white", "en"),
    ("کرم", "cream", "fa"), ("cream", "cream", "en"),
    ("ذغالی", "charcoal", "fa"), ("زغالی", "charcoal", "fa"), ("charcoal", "charcoal", "en"),
    ("سرمه ای", "navy", "fa"), ("navy", "navy", "en"),
    ("طوسی", "gray", "fa"), ("خاکستری", "gray", "fa"), ("gray", "gray", "en"),
    ("قهوه ای", "brown", "fa"), ("brown", "brown", "en"),
    ("نسکافه ای", "coffee", "fa"), ("coffee", "coffee", "en"),
]
SIZE_DEFAULTS = [
    ("اس", "S", None), ("s", "S", None), ("small", "S", None),
    ("ام", "M", None), ("m", "M", None), ("medium", "M", None),
    ("ال", "L", None), ("l", "L", None), ("large", "L", None),
    ("ایکس لارج", "XL", None), ("xl", "XL", None),
    ("فری سایز", "FREE", None), ("فری‌سایز", "FREE", None), ("تک سایز", "FREE", None), ("one size", "FREE", None),
    ("36", "36", None), ("38", "38", None), ("40", "40", None), ("42", "42", None),
]


def upgrade() -> None:
    op.add_column("color_aliases", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.add_column("color_aliases", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.add_column("size_aliases", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.add_column("size_aliases", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_index("ix_color_aliases_created_at", "color_aliases", ["created_at"])
    op.create_index("ix_size_aliases_created_at", "size_aliases", ["created_at"])

    op.create_table(
        "unavailable_demand_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("shop_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("requested_color_raw", sa.String(length=128), nullable=True),
        sa.Column("requested_color_normalized", sa.String(length=128), nullable=True),
        sa.Column("requested_size_raw", sa.String(length=128), nullable=True),
        sa.Column("requested_size_normalized", sa.String(length=128), nullable=True),
        sa.Column("requested_quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=True),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("estimated_lost_revenue", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("shop_id", "product_id", "requested_color_normalized", "requested_size_normalized", "reason", "conversation_id", "customer_id", "created_at"):
        op.create_index(f"ix_unavailable_demand_logs_{column}", "unavailable_demand_logs", [column])

    color_table = sa.table(
        "color_aliases",
        sa.column("id"),
        sa.column("shop_id"),
        sa.column("raw_value"),
        sa.column("normalized_value"),
        sa.column("language"),
        sa.column("is_active"),
    )
    size_table = sa.table(
        "size_aliases",
        sa.column("id"),
        sa.column("shop_id"),
        sa.column("raw_value"),
        sa.column("normalized_value"),
        sa.column("category"),
        sa.column("is_active"),
    )
    op.bulk_insert(
        color_table,
        [
            {
                "id": uuid.uuid4(),
                "shop_id": None,
                "raw_value": raw,
                "normalized_value": normalized,
                "language": language,
                "is_active": True,
            }
            for raw, normalized, language in COLOR_DEFAULTS
        ],
    )
    op.bulk_insert(
        size_table,
        [
            {
                "id": uuid.uuid4(),
                "shop_id": None,
                "raw_value": raw,
                "normalized_value": normalized,
                "category": category,
                "is_active": True,
            }
            for raw, normalized, category in SIZE_DEFAULTS
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM color_aliases WHERE shop_id IS NULL")
    op.execute("DELETE FROM size_aliases WHERE shop_id IS NULL")
    op.drop_table("unavailable_demand_logs")
    op.drop_index("ix_size_aliases_created_at", table_name="size_aliases")
    op.drop_index("ix_color_aliases_created_at", table_name="color_aliases")
    op.drop_column("size_aliases", "updated_at")
    op.drop_column("size_aliases", "created_at")
    op.drop_column("color_aliases", "updated_at")
    op.drop_column("color_aliases", "created_at")
