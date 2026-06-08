"""Sprint E simulation flags on messages, orders, agent_runs, suggested_replies

Revision ID: 20260608_0014
Revises: 20260608_0013
Create Date: 2026-06-08 22:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260608_0014"
down_revision: str | None = "20260608_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SIMULATION_TABLES = ("messages", "orders", "agent_runs", "suggested_replies")


def upgrade() -> None:
    for table in _SIMULATION_TABLES:
        op.add_column(
            table,
            sa.Column("is_simulation", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.create_index(f"ix_{table}_is_simulation", table, ["is_simulation"])


def downgrade() -> None:
    for table in reversed(_SIMULATION_TABLES):
        op.drop_index(f"ix_{table}_is_simulation", table_name=table)
        op.drop_column(table, "is_simulation")
