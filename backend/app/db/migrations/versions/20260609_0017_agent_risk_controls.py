"""agent risk controls and decision trace completeness

Revision ID: 20260609_0017
Revises: 20260608_0016
Create Date: 2026-06-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260609_0017"
down_revision = "20260608_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shop_agent_settings", sa.Column("risk_policy_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("agent_decision_traces", sa.Column("normalized_slots", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("agent_decision_traces", sa.Column("risk_score", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))


def downgrade() -> None:
    op.drop_column("agent_decision_traces", "risk_score")
    op.drop_column("agent_decision_traces", "normalized_slots")
    op.drop_column("shop_agent_settings", "risk_policy_json")
