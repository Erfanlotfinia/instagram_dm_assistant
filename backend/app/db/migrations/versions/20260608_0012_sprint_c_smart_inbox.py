"""Sprint C smart inbox priority and conversation events

Revision ID: 20260608_0012
Revises: 20260608_0011
Create Date: 2026-06-08 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260608_0012"
down_revision: str | None = "20260608_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        priority_level = postgresql.ENUM(
            "urgent", "high", "medium", "low",
            name="conversation_priority_level",
            create_type=False,
        )
        event_type = postgresql.ENUM(
            "inbound_message_received",
            "outbound_message_sent",
            "suggested_reply_created",
            "suggested_reply_approved",
            "product_resolved",
            "variant_resolved",
            "inventory_checked",
            "draft_order_created",
            "customer_info_completed",
            "confirmation_requested",
            "payment_link_sent",
            "payment_received",
            "order_shipped",
            "handoff_required",
            "operator_took_over",
            "operator_released_to_agent",
            "order_cancelled",
            "conversation_assigned",
            "customer_profile_updated",
            name="conversation_event_type",
            create_type=False,
        )
        priority_level.create(bind, checkfirst=True)
        event_type.create(bind, checkfirst=True)
    else:
        priority_level = sa.Enum("urgent", "high", "medium", "low", name="conversation_priority_level")
        event_type = sa.Enum(
            "inbound_message_received",
            "outbound_message_sent",
            "suggested_reply_created",
            "suggested_reply_approved",
            "product_resolved",
            "variant_resolved",
            "inventory_checked",
            "draft_order_created",
            "customer_info_completed",
            "confirmation_requested",
            "payment_link_sent",
            "payment_received",
            "order_shipped",
            "handoff_required",
            "operator_took_over",
            "operator_released_to_agent",
            "order_cancelled",
            "conversation_assigned",
            "customer_profile_updated",
            name="conversation_event_type",
        )

    op.add_column(
        "conversations",
        sa.Column("priority_score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "conversations",
        sa.Column("priority_level", priority_level, nullable=False, server_default="low"),
    )
    op.add_column("conversations", sa.Column("priority_reason", sa.Text(), nullable=True))
    op.add_column(
        "conversations",
        sa.Column("last_operator_action_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("needs_attention", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    for col in ("priority_score", "priority_level", "needs_attention"):
        op.create_index(f"ix_conversations_{col}", "conversations", [col])

    op.create_table(
        "conversation_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ("conversation_id", "event_type", "created_by_user_id", "created_at"):
        op.create_index(f"ix_conversation_events_{col}", "conversation_events", [col])


def downgrade() -> None:
    op.drop_table("conversation_events")
    for col in ("needs_attention", "last_operator_action_at", "priority_reason", "priority_level", "priority_score"):
        op.drop_column("conversations", col)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS conversation_event_type")
        op.execute("DROP TYPE IF EXISTS conversation_priority_level")
