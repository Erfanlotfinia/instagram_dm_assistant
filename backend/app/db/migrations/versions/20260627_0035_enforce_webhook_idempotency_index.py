"""enforce webhook idempotency index

Revision ID: 20260627_0035
Revises: 20260627_0034
Create Date: 2026-06-27 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op

revision: str = "20260627_0035"
down_revision: str | None = "20260627_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Older dev/test databases may have duplicate non-null webhook idempotency rows
    # from before database-enforced webhook dedupe. Keep the oldest row and remove
    # later duplicates so the partial unique index can be created safely.
    op.execute(
        """
        DELETE FROM webhook_events duplicate
        USING webhook_events original
        WHERE duplicate.provider = original.provider
          AND duplicate.idempotency_key = original.idempotency_key
          AND duplicate.idempotency_key IS NOT NULL
          AND duplicate.created_at > original.created_at
        """
    )
    op.execute(
        """
        DELETE FROM webhook_events duplicate
        USING webhook_events original
        WHERE duplicate.provider = original.provider
          AND duplicate.idempotency_key = original.idempotency_key
          AND duplicate.idempotency_key IS NOT NULL
          AND duplicate.created_at = original.created_at
          AND duplicate.id::text > original.id::text
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_webhook_events_provider_idempotency
        ON webhook_events (provider, idempotency_key)
        WHERE idempotency_key IS NOT NULL
        """
    )


def downgrade() -> None:
    # This index may have been introduced by an earlier migration in existing
    # databases, so do not drop it when downgrading this drift-repair migration.
    pass
