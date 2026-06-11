"""Sprint B agent modes and suggested replies

Revision ID: 20260608_0011
Revises: 20260607_0010
Create Date: 2026-06-08 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260608_0011"
down_revision: str | None = "20260607_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        selling_style = postgresql.ENUM(
            "educational",
            "balanced",
            "promotional",
            name="selling_style",
            create_type=False,
        )
        selling_style.create(bind, checkfirst=True)
        with op.get_context().autocommit_block():
            for value in ("friendly", "formal", "concise"):
                op.execute(f"ALTER TYPE selling_style ADD VALUE IF NOT EXISTS '{value}'")
        agent_mode = postgresql.ENUM(
            "copilot", "controlled_autopilot", "human_first", name="agent_mode", create_type=False
        )
        agent_mode.create(bind, checkfirst=True)
        suggested_status = postgresql.ENUM(
            "pending", "approved", "edited", "rejected", "sent",
            name="suggested_reply_status",
            create_type=False,
        )
        suggested_by = postgresql.ENUM(
            "agent", "operator", name="suggested_reply_generated_by", create_type=False
        )
        suggested_status.create(bind, checkfirst=True)
        suggested_by.create(bind, checkfirst=True)
    else:
        agent_mode = sa.Enum("copilot", "controlled_autopilot", "human_first", name="agent_mode")
        suggested_status = sa.Enum("pending", "approved", "edited", "rejected", "sent", name="suggested_reply_status")
        suggested_by = sa.Enum("agent", "operator", name="suggested_reply_generated_by")

    op.add_column("shop_agent_settings", sa.Column("mode", agent_mode, nullable=False, server_default="copilot"))
    op.alter_column("shop_agent_settings", "selling_style", server_default="friendly")

    op.create_table(
        "suggested_replies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("shop_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=True),
        sa.Column("suggested_text", sa.Text(), nullable=False),
        sa.Column("status", suggested_status, nullable=False, server_default="pending"),
        sa.Column("generated_by", suggested_by, nullable=False, server_default="agent"),
        sa.Column("approved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("edited_text", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ("shop_id", "conversation_id", "message_id", "status", "approved_by_user_id", "created_at"):
        op.create_index(f"ix_suggested_replies_{col}", "suggested_replies", [col])


def downgrade() -> None:
    op.drop_table("suggested_replies")
    op.drop_column("shop_agent_settings", "mode")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS suggested_reply_generated_by")
        op.execute("DROP TYPE IF EXISTS suggested_reply_status")
        op.execute("DROP TYPE IF EXISTS agent_mode")
