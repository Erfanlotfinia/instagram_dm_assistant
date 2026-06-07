"""Sprint 6 shop agent settings

Revision ID: 20260607_0006
Revises: 20260607_0005
Create Date: 2026-06-07 20:00:00.000000
"""
import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260607_0006"
down_revision: str | None = "20260607_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_AGENT_SETTINGS = {
    "auto_reply_enabled": True,
    "intent_confidence_threshold": 0.65,
    "slots_confidence_threshold": 0.60,
    "handoff_mode": "automatic",
    "default_language": "fa",
    "low_stock_threshold": 5,
}


def upgrade() -> None:
    op.add_column(
        "shops",
        sa.Column(
            "agent_settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text(f"'{json.dumps(DEFAULT_AGENT_SETTINGS)}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("shops", "agent_settings")
