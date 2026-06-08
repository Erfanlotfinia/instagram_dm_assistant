"""Sprint F pilot readiness: failed jobs hardening and agent run idempotency

Revision ID: 20260608_0015
Revises: 20260608_0014
Create Date: 2026-06-08 23:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260608_0015"
down_revision: str | None = "20260608_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

failed_job_status = postgresql.ENUM("failed", "retried", "ignored", name="failed_job_status", create_type=False)


def upgrade() -> None:
    op.execute("CREATE TYPE failed_job_status AS ENUM ('failed', 'retried', 'ignored')")

    op.add_column("failed_jobs", sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("failed_jobs", sa.Column("traceback", sa.Text(), nullable=True))
    op.add_column(
        "failed_jobs",
        sa.Column(
            "status",
            failed_job_status,
            nullable=False,
            server_default="failed",
        ),
    )
    op.add_column(
        "failed_jobs",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(op.f("ix_failed_jobs_shop_id"), "failed_jobs", ["shop_id"], unique=False)
    op.create_index(op.f("ix_failed_jobs_status"), "failed_jobs", ["status"], unique=False)
    op.create_foreign_key(
        "fk_failed_jobs_shop_id_shops",
        "failed_jobs",
        "shops",
        ["shop_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_unique_constraint("uq_agent_runs_input_message_id", "agent_runs", ["input_message_id"])


def downgrade() -> None:
    op.drop_constraint("uq_agent_runs_input_message_id", "agent_runs", type_="unique")
    op.drop_constraint("fk_failed_jobs_shop_id_shops", "failed_jobs", type_="foreignkey")
    op.drop_index(op.f("ix_failed_jobs_status"), table_name="failed_jobs")
    op.drop_index(op.f("ix_failed_jobs_shop_id"), table_name="failed_jobs")
    op.drop_column("failed_jobs", "updated_at")
    op.drop_column("failed_jobs", "status")
    op.drop_column("failed_jobs", "traceback")
    op.drop_column("failed_jobs", "shop_id")
    op.execute("DROP TYPE failed_job_status")
