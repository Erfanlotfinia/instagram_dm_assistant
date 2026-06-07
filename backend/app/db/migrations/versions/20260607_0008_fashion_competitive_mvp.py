"""fashion competitive mvp

Revision ID: 20260607_0008
Revises: 20260607_0007
Create Date: 2026-06-07
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260607_0008"
down_revision = "20260607_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shops", sa.Column("onboarding_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("conversations", sa.Column("is_simulation", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("conversations", sa.Column("suggested_outbound", sa.Text(), nullable=True))
    op.add_column("conversations", sa.Column("preview_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("conversations", sa.Column("preview_reason", sa.Text(), nullable=True))
    op.create_index("ix_conversations_is_simulation", "conversations", ["is_simulation"])
    op.add_column("conversation_slots", sa.Column("normalized_color", sa.String(length=64), nullable=True))
    op.add_column("conversation_slots", sa.Column("normalized_size", sa.String(length=64), nullable=True))
    op.add_column("conversation_slots", sa.Column("product_candidates", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("conversation_slots", sa.Column("variant_alternatives", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("products", sa.Column("category", sa.String(length=128), nullable=True))
    op.add_column("products", sa.Column("size_chart", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("product_variants", sa.Column("normalized_color", sa.String(length=64), nullable=True))
    op.add_column("product_variants", sa.Column("normalized_size", sa.String(length=64), nullable=True))
    op.create_index("ix_product_variants_normalized_color", "product_variants", ["normalized_color"])
    op.create_index("ix_product_variants_normalized_size", "product_variants", ["normalized_size"])
    op.add_column("instagram_product_maps", sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("instagram_product_maps", sa.Column("admin_label", sa.String(length=255), nullable=True))
    op.add_column("orders", sa.Column("risk_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("orders", sa.Column("approval_source", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("payment_callback_status", sa.String(length=64), nullable=True))
    op.add_column("payments", sa.Column("callback_processed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "agent_decision_audits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("shop_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=True),
        sa.Column("input_message", sa.Text(), nullable=True),
        sa.Column("extracted_intent", sa.String(length=128), nullable=True),
        sa.Column("extracted_slots", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("product_candidates", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("chosen_product_id", sa.UUID(), nullable=True),
        sa.Column("variant_resolver_result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("inventory_result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("next_state", sa.String(length=128), nullable=False),
        sa.Column("outbound_message", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chosen_product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "failed_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("queue_name", sa.String(length=128), nullable=False),
        sa.Column("job_type", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("failed_jobs")
    op.drop_table("agent_decision_audits")
    op.drop_column("payments", "callback_processed_at")
    op.drop_column("orders", "payment_callback_status")
    op.drop_column("orders", "approval_source")
    op.drop_column("orders", "risk_flags")
    op.drop_column("instagram_product_maps", "admin_label")
    op.drop_column("instagram_product_maps", "display_order")
    op.drop_index("ix_product_variants_normalized_size", table_name="product_variants")
    op.drop_index("ix_product_variants_normalized_color", table_name="product_variants")
    op.drop_column("product_variants", "normalized_size")
    op.drop_column("product_variants", "normalized_color")
    op.drop_column("products", "size_chart")
    op.drop_column("products", "category")
    op.drop_column("conversation_slots", "variant_alternatives")
    op.drop_column("conversation_slots", "product_candidates")
    op.drop_column("conversation_slots", "normalized_size")
    op.drop_column("conversation_slots", "normalized_color")
    op.drop_index("ix_conversations_is_simulation", table_name="conversations")
    op.drop_column("conversations", "preview_reason")
    op.drop_column("conversations", "preview_required")
    op.drop_column("conversations", "suggested_outbound")
    op.drop_column("conversations", "is_simulation")
    op.drop_column("shops", "onboarding_flags")
