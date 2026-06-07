"""Sprint 7: audit log hardening and payment idempotency

Revision ID: 20260607_0007
Revises: 20260607_0006
Create Date: 2026-06-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260607_0007"
down_revision: Union[str, None] = "20260607_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("admin_audit_logs", "shop_id", existing_type=sa.UUID(), nullable=True)
    op.alter_column("admin_audit_logs", "entity_id", existing_type=sa.String(length=128), nullable=True)
    op.add_column("admin_audit_logs", sa.Column("ip_address", sa.String(length=64), nullable=True))
    op.add_column("admin_audit_logs", sa.Column("user_agent", sa.String(length=512), nullable=True))

    op.create_index(
        "uq_payments_provider_reference",
        "payments",
        ["provider_reference"],
        unique=True,
        postgresql_where=sa.text("provider_reference IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_payments_provider_reference", table_name="payments")
    op.drop_column("admin_audit_logs", "user_agent")
    op.drop_column("admin_audit_logs", "ip_address")
    op.alter_column("admin_audit_logs", "entity_id", existing_type=sa.String(length=128), nullable=False)
    op.alter_column("admin_audit_logs", "shop_id", existing_type=sa.UUID(), nullable=False)
