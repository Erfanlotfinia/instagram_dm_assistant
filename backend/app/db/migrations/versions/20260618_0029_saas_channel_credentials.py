"""SaaS per-shop channel credentials

Revision ID: 20260618_0029
Revises: 20260615_0028
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260618_0029"
down_revision: str | None = "20260615_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("channel_accounts", sa.Column("webhook_url", sa.Text(), nullable=True))
    op.alter_column("channel_accounts", "encrypted_access_token", new_column_name="access_token_encrypted")
    op.alter_column("channel_accounts", "encrypted_bot_token", new_column_name="bot_token_encrypted")
    # The legacy column stored webhook secrets in plaintext. Do not relabel
    # those values as encrypted; administrators must re-enter them write-only.
    op.execute("UPDATE channel_accounts SET webhook_secret = NULL WHERE webhook_secret IS NOT NULL")
    op.alter_column("channel_accounts", "webhook_secret", new_column_name="webhook_secret_encrypted")
    op.add_column("channel_accounts", sa.Column("refresh_token_encrypted", sa.Text(), nullable=True))
    op.add_column("channel_accounts", sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("channel_accounts", sa.Column("scopes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("channel_accounts", sa.Column("last_validation_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("channel_accounts", sa.Column("last_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("channel_accounts", "last_error")
    op.drop_column("channel_accounts", "last_validation_at")
    op.drop_column("channel_accounts", "scopes_json")
    op.drop_column("channel_accounts", "token_expires_at")
    op.drop_column("channel_accounts", "refresh_token_encrypted")
    op.alter_column("channel_accounts", "webhook_secret_encrypted", new_column_name="webhook_secret")
    op.alter_column("channel_accounts", "bot_token_encrypted", new_column_name="encrypted_bot_token")
    op.alter_column("channel_accounts", "access_token_encrypted", new_column_name="encrypted_access_token")
    op.drop_column("channel_accounts", "webhook_url")
