"""trust layer core

Revision ID: 20260609_0021
Revises: 20260609_0020
Create Date: 2026-06-09 22:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260609_0021"
down_revision: str | None = "20260609_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

simulator_run_source_type = postgresql.ENUM(
    "manual", "scenario_pack", "incident_replay",
    name="simulator_run_source_type", create_type=False,
)
simulator_run_status = postgresql.ENUM(
    "running", "completed", "failed",
    name="simulator_run_status", create_type=False,
)
trace_event_type = postgresql.ENUM(
    "retrieval_evidence", "slots_extracted", "confidence_band",
    "policy_check", "action_attempted", "action_blocked",
    name="trace_event_type", create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE TYPE simulator_run_source_type AS ENUM ('manual', 'scenario_pack', 'incident_replay')")
    op.execute("CREATE TYPE simulator_run_status AS ENUM ('running', 'completed', 'failed')")
    op.execute(
        "CREATE TYPE trace_event_type AS ENUM ("
        "'retrieval_evidence', 'slots_extracted', 'confidence_band', "
        "'policy_check', 'action_attempted', 'action_blocked')"
    )

    op.create_table(
        "policy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "version", name="uq_policy_versions_shop_version"),
    )
    for col in ["shop_id", "version", "is_active", "created_by_user_id", "created_at"]:
        op.create_index(f"ix_policy_versions_{col}", "policy_versions", [col], unique=False)

    op.create_table(
        "simulator_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("source_type", simulator_run_source_type, nullable=False, server_default="manual"),
        sa.Column("model_version", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("policy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("catalog_snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("catalog_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", simulator_run_status, nullable=False, server_default="running"),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("diff_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ["shop_id", "created_by_user_id", "source_type", "policy_version_id", "catalog_snapshot_hash", "status", "started_at"]:
        op.create_index(f"ix_simulator_runs_{col}", "simulator_runs", [col], unique=False)

    op.create_table(
        "simulator_run_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_key", sa.String(length=128), nullable=False),
        sa.Column("input_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("expected_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("actual_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("diff_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["simulator_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ["run_id", "item_key", "passed", "trace_id", "conversation_id", "created_at"]:
        op.create_index(f"ix_simulator_run_items_{col}", "simulator_run_items", [col], unique=False)

    op.create_table(
        "trace_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("event_type", trace_event_type, nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ["trace_id", "shop_id", "conversation_id", "event_type", "created_at"]:
        op.create_index(f"ix_trace_events_{col}", "trace_events", [col], unique=False)


def downgrade() -> None:
    op.drop_table("trace_events")
    op.drop_table("simulator_run_items")
    op.drop_table("simulator_runs")
    op.drop_table("policy_versions")
    op.execute("DROP TYPE IF EXISTS trace_event_type")
    op.execute("DROP TYPE IF EXISTS simulator_run_status")
    op.execute("DROP TYPE IF EXISTS simulator_run_source_type")
