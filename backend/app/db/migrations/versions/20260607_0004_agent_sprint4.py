"""Sprint 4 agent workflow schema

Revision ID: 20260607_0004
Revises: 20260607_0003
Create Date: 2026-06-07 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260607_0004"
down_revision: str | None = "20260607_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

agent_workflow_state = postgresql.ENUM(
    "idle",
    "waiting_for_product",
    "waiting_for_variant",
    "waiting_for_customer_info",
    "waiting_for_confirmation",
    "waiting_for_payment",
    "paid",
    "sent_to_shipping",
    "completed",
    "cancelled",
    "human_handoff",
    name="agent_workflow_state",
    create_type=False,
)
agent_run_status = postgresql.ENUM("success", "failed", name="agent_run_status", create_type=False)


def upgrade() -> None:
    agent_workflow_state.create(op.get_bind(), checkfirst=True)
    agent_run_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "conversations",
        sa.Column("workflow_state", agent_workflow_state, nullable=False, server_default="idle"),
    )
    op.add_column(
        "conversations",
        sa.Column("agent_failure_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "conversations",
        sa.Column("agent_paused", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("input_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", agent_run_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["input_message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_runs_conversation_id"), "agent_runs", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_agent_runs_created_at"), "agent_runs", ["created_at"], unique=False)
    op.create_index(
        op.f("ix_agent_runs_input_message_id"), "agent_runs", ["input_message_id"], unique=False
    )

    op.create_table(
        "conversation_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("instagram_post_url", sa.String(length=2048), nullable=True),
        sa.Column("color", sa.String(length=64), nullable=True),
        sa.Column("size", sa.String(length=64), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("postal_code", sa.String(length=32), nullable=True),
        sa.Column("missing_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_variant_id"], ["product_variants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversation_slots_conversation_id"),
        "conversation_slots",
        ["conversation_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_conversation_slots_product_id"), "conversation_slots", ["product_id"], unique=False
    )
    op.create_index(
        op.f("ix_conversation_slots_product_variant_id"),
        "conversation_slots",
        ["product_variant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_conversation_slots_product_variant_id"), table_name="conversation_slots")
    op.drop_index(op.f("ix_conversation_slots_product_id"), table_name="conversation_slots")
    op.drop_index(op.f("ix_conversation_slots_conversation_id"), table_name="conversation_slots")
    op.drop_table("conversation_slots")

    op.drop_index(op.f("ix_agent_runs_input_message_id"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_created_at"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_conversation_id"), table_name="agent_runs")
    op.drop_table("agent_runs")

    op.drop_column("conversations", "agent_paused")
    op.drop_column("conversations", "agent_failure_count")
    op.drop_column("conversations", "workflow_state")

    agent_run_status.drop(op.get_bind(), checkfirst=True)
    agent_workflow_state.drop(op.get_bind(), checkfirst=True)
