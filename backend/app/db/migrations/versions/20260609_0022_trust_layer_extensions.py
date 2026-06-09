"""trust layer extensions

Revision ID: 20260609_0022
Revises: 20260609_0021
Create Date: 2026-06-09 22:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260609_0022"
down_revision: str | None = "20260609_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

pilot_operating_mode = postgresql.ENUM(
    "shadow", "copilot", "autonomous_low_risk",
    name="pilot_operating_mode", create_type=False,
)
pilot_mode_scope = postgresql.ENUM(
    "global", "category", "campaign",
    name="pilot_mode_scope", create_type=False,
)
scenario_pack_type = postgresql.ENUM(
    "handcrafted", "synthetic", "incident_replay",
    name="scenario_pack_type", create_type=False,
)
incident_severity = postgresql.ENUM(
    "low", "medium", "high", "critical",
    name="incident_severity", create_type=False,
)
incident_status = postgresql.ENUM(
    "open", "mitigated", "resolved",
    name="incident_status", create_type=False,
)
incident_trigger = postgresql.ENUM(
    "emergency_stop", "policy_breach", "manual",
    name="incident_trigger", create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE TYPE pilot_operating_mode AS ENUM ('shadow', 'copilot', 'autonomous_low_risk')")
    op.execute("CREATE TYPE pilot_mode_scope AS ENUM ('global', 'category', 'campaign')")
    op.execute("CREATE TYPE scenario_pack_type AS ENUM ('handcrafted', 'synthetic', 'incident_replay')")
    op.execute("CREATE TYPE incident_severity AS ENUM ('low', 'medium', 'high', 'critical')")
    op.execute("CREATE TYPE incident_status AS ENUM ('open', 'mitigated', 'resolved')")
    op.execute("CREATE TYPE incident_trigger AS ENUM ('emergency_stop', 'policy_breach', 'manual')")

    op.add_column(
        "pilot_settings",
        sa.Column("operating_mode", pilot_operating_mode, nullable=False, server_default="copilot"),
    )
    op.add_column(
        "pilot_settings",
        sa.Column("category_overrides_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "pilot_settings",
        sa.Column("campaign_overrides_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "scenario_packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("pack_type", scenario_pack_type, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scenarios_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_golden", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ["shop_id", "pack_type", "is_golden", "created_by_user_id"]:
        op.create_index(f"ix_scenario_packs_{col}", "scenario_packs", [col], unique=False)

    op.create_table(
        "pilot_mode_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_mode", pilot_operating_mode, nullable=True),
        sa.Column("new_mode", pilot_operating_mode, nullable=False),
        sa.Column("scope", pilot_mode_scope, nullable=False, server_default="global"),
        sa.Column("scope_ref", sa.String(length=255), nullable=True),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ["shop_id", "changed_by_user_id", "created_at"]:
        op.create_index(f"ix_pilot_mode_history_{col}", "pilot_mode_history", [col], unique=False)

    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("severity", incident_severity, nullable=False),
        sa.Column("status", incident_status, nullable=False, server_default="open"),
        sa.Column("trigger", incident_trigger, nullable=False),
        sa.Column("opened_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["opened_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ["shop_id", "severity", "status", "trigger", "opened_by_user_id", "opened_at"]:
        op.create_index(f"ix_incidents_{col}", "incidents", [col], unique=False)

    op.create_table(
        "incident_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("affected_conversation_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ["incident_id", "event_type", "actor_user_id", "created_at"]:
        op.create_index(f"ix_incident_events_{col}", "incident_events", [col], unique=False)


def downgrade() -> None:
    op.drop_table("incident_events")
    op.drop_table("incidents")
    op.drop_table("pilot_mode_history")
    op.drop_table("scenario_packs")
    op.drop_column("pilot_settings", "campaign_overrides_json")
    op.drop_column("pilot_settings", "category_overrides_json")
    op.drop_column("pilot_settings", "operating_mode")
    op.execute("DROP TYPE IF EXISTS incident_trigger")
    op.execute("DROP TYPE IF EXISTS incident_status")
    op.execute("DROP TYPE IF EXISTS incident_severity")
    op.execute("DROP TYPE IF EXISTS scenario_pack_type")
    op.execute("DROP TYPE IF EXISTS pilot_mode_scope")
    op.execute("DROP TYPE IF EXISTS pilot_operating_mode")
