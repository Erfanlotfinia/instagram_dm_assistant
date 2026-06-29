"""refresh session family

Revision ID: 20260629_0036
Revises: 20260627_0035
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260629_0036"
down_revision = "20260627_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "refresh_sessions",
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "refresh_sessions",
        sa.Column("parent_session_id", sa.String(length=64), nullable=True),
    )
    op.execute("UPDATE refresh_sessions SET family_id = id WHERE family_id IS NULL")
    op.alter_column("refresh_sessions", "family_id", nullable=False)
    op.create_index("ix_refresh_sessions_family_id", "refresh_sessions", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_refresh_sessions_family_id", table_name="refresh_sessions")
    op.drop_column("refresh_sessions", "parent_session_id")
    op.drop_column("refresh_sessions", "family_id")
