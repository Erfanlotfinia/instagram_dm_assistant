"""TRL validation simulator

Revision ID: 20260608_0016
Revises: 20260608_0015
Create Date: 2026-06-08 23:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260608_0016"
down_revision: str | None = "20260608_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trl_validation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("total_scenarios", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_scenarios", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_scenarios", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trl_validation_runs_shop_id"), "trl_validation_runs", ["shop_id"], unique=False)
    op.create_index(op.f("ix_trl_validation_runs_status"), "trl_validation_runs", ["status"], unique=False)
    op.create_index(op.f("ix_trl_validation_runs_started_at"), "trl_validation_runs", ["started_at"], unique=False)
    op.create_index(op.f("ix_trl_validation_runs_created_by_user_id"), "trl_validation_runs", ["created_by_user_id"], unique=False)
    op.create_table(
        "trl_validation_scenario_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_id", sa.String(length=128), nullable=False),
        sa.Column("input_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("expected_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("actual_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("failure_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("processing_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["trl_validation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ["run_id", "scenario_id", "passed", "conversation_id", "order_id", "created_at"]:
        op.create_index(f"ix_trl_validation_scenario_results_{col}", "trl_validation_scenario_results", [col], unique=False)


def downgrade() -> None:
    op.drop_table("trl_validation_scenario_results")
    op.drop_table("trl_validation_runs")
