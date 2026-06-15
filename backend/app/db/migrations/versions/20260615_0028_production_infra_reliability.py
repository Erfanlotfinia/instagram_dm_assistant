"""production infra reliability tables and indexes

Revision ID: 20260615_0028
Revises: 20260613_0027
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260615_0028"
down_revision = "20260613_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_store",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", sa.String(128), nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("causation_id", sa.String(128)),
        sa.Column("partition_key", sa.String(512), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "event_id", name="uq_event_store_tenant_event"),
    )
    op.create_index("ix_event_store_tenant_created", "event_store", ["tenant_id", "created_at"])
    op.create_index("ix_event_store_conversation", "event_store", ["tenant_id", "conversation_id", "created_at"])
    op.create_index("ix_event_store_correlation", "event_store", ["correlation_id"])

    op.create_table(
        "consumer_idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("consumer_group", sa.String(128), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("partition", sa.Integer(), nullable=False),
        sa.Column("offset", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="processed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "event_id", "consumer_group", name="uq_consumer_idempotency"),
    )
    op.create_index("ix_consumer_idempotency_group_created", "consumer_idempotency_keys", ["consumer_group", "created_at"])

    op.add_column("orders", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("payments", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("product_variants", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("product_variants", "version")
    op.drop_column("payments", "version")
    op.drop_column("orders", "version")
    op.drop_table("consumer_idempotency_keys")
    op.drop_table("event_store")
