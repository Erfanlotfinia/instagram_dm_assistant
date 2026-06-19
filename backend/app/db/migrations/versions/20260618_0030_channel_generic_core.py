"""remove Instagram requirements from core messaging records

Revision ID: 20260618_0030
Revises: 20260618_0029
Create Date: 2026-06-18 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260618_0030"
down_revision: str | None = "20260618_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("display_name", sa.String(255), nullable=True))
    op.add_column("customers", sa.Column("email", sa.String(320), nullable=True))
    op.add_column(
        "customers",
        sa.Column(
            "primary_channel_provider",
            postgresql.ENUM(name="channel_provider", create_type=False),
            nullable=True,
        ),
    )
    op.add_column(
        "customers", sa.Column("primary_external_user_id", sa.String(128), nullable=True)
    )
    op.create_index(
        op.f("ix_customers_primary_channel_provider"),
        "customers",
        ["primary_channel_provider"],
    )
    op.create_index(
        op.f("ix_customers_primary_external_user_id"),
        "customers",
        ["primary_external_user_id"],
    )
    op.execute(
        """
        UPDATE customers
        SET display_name = full_name,
            primary_channel_provider = 'instagram'::channel_provider,
            primary_external_user_id = instagram_user_id
        WHERE instagram_user_id IS NOT NULL
        """
    )
    op.alter_column("customers", "instagram_user_id", nullable=True)
    op.drop_constraint("uq_customers_shop_instagram_user", "customers", type_="unique")

    op.add_column(
        "channel_contact_identities",
        sa.Column("external_chat_id", sa.String(128), nullable=True),
    )
    op.create_index(
        op.f("ix_channel_contact_identities_external_chat_id"),
        "channel_contact_identities",
        ["external_chat_id"],
    )
    op.alter_column("channel_contact_identities", "raw_profile_json", nullable=True)
    op.execute(
        """
        INSERT INTO channel_contact_identities (
            id, shop_id, customer_id, provider, channel_account_id,
            external_user_id, display_name, phone, raw_profile_json,
            created_at, updated_at
        )
        SELECT gen_random_uuid(), c.shop_id, c.id, 'instagram'::channel_provider,
               ca.id, c.instagram_user_id, c.full_name, c.phone, '{}'::jsonb,
               c.created_at, c.updated_at
        FROM customers c
        JOIN channel_accounts ca
          ON ca.shop_id = c.shop_id
         AND ca.provider = 'instagram'::channel_provider
        WHERE c.instagram_user_id IS NOT NULL
        ON CONFLICT (shop_id, provider, channel_account_id, external_user_id)
        DO UPDATE SET customer_id = EXCLUDED.customer_id
        """
    )
    op.execute("DELETE FROM channel_contact_identities WHERE customer_id IS NULL")
    op.alter_column("channel_contact_identities", "customer_id", nullable=False)
    op.drop_constraint(
        "channel_contact_identities_customer_id_fkey",
        "channel_contact_identities",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "channel_contact_identities_customer_id_fkey",
        "channel_contact_identities",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.add_column(
        "conversations",
        sa.Column("channel_account_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("external_conversation_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "conversations", sa.Column("external_thread_id", sa.String(128), nullable=True)
    )
    op.create_foreign_key(
        "conversations_channel_account_id_fkey",
        "conversations",
        "channel_accounts",
        ["channel_account_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        """
        INSERT INTO channel_accounts (
            id, shop_id, provider, display_name, external_account_id, bot_username,
            access_token_encrypted, status, capabilities_json, settings_json,
            created_at, updated_at
        )
        SELECT gen_random_uuid(), ia.shop_id, 'instagram'::channel_provider,
               ia.username, ia.ig_user_id, ia.username, ia.access_token_encrypted,
               'connected'::channel_account_status,
               '{"supports_webhook": true, "supports_text": true, "supports_images": true}'::jsonb,
               jsonb_build_object('legacy_instagram_account_id', ia.id::text),
               ia.created_at, ia.updated_at
        FROM instagram_accounts ia
        WHERE NOT EXISTS (
            SELECT 1
            FROM channel_accounts ca
            WHERE ca.shop_id = ia.shop_id
              AND ca.provider = 'instagram'::channel_provider
              AND ca.settings_json->>'legacy_instagram_account_id' = ia.id::text
        )
        ON CONFLICT (shop_id, provider, external_account_id)
        DO UPDATE SET settings_json =
            COALESCE(channel_accounts.settings_json, '{}'::jsonb)
            || EXCLUDED.settings_json
        """
    )
    op.execute(
        """
        UPDATE conversations c
        SET channel_account_id = ca.id,
            external_conversation_id = COALESCE(
                c.channel_conversation_id, c.channel_customer_id, c.id::text
            )
        FROM channel_accounts ca
        WHERE ca.shop_id = c.shop_id
          AND ca.provider::text = c.channel_provider
          AND (
              c.instagram_account_id IS NULL
              OR ca.settings_json->>'legacy_instagram_account_id' = c.instagram_account_id::text
          )
        """
    )
    op.alter_column("conversations", "instagram_account_id", nullable=True)
    op.alter_column("conversations", "channel_account_id", nullable=False)
    op.alter_column("conversations", "external_conversation_id", nullable=False)
    for column in ("channel_account_id", "external_conversation_id", "external_thread_id"):
        op.create_index(op.f(f"ix_conversations_{column}"), "conversations", [column])

    message_columns = [
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "channel_provider",
            postgresql.ENUM(name="channel_provider", create_type=False),
            nullable=True,
        ),
        sa.Column("channel_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_message_id", sa.String(128), nullable=True),
        sa.Column("external_update_id", sa.String(128), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("raw_payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("normalized_payload_json", postgresql.JSONB(), nullable=True),
    ]
    for column in message_columns:
        op.add_column("messages", column)
    op.create_foreign_key(
        "messages_shop_id_fkey", "messages", "shops", ["shop_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "messages_customer_id_fkey",
        "messages",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "messages_channel_account_id_fkey",
        "messages",
        "channel_accounts",
        ["channel_account_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        """
        UPDATE messages m
        SET shop_id = c.shop_id,
            customer_id = c.customer_id,
            channel_provider = c.channel_provider::channel_provider,
            channel_account_id = c.channel_account_id,
            external_message_id = COALESCE(m.channel_message_id, m.instagram_message_id),
            content = m.text,
            raw_payload_json = m.raw_payload
        FROM conversations c
        WHERE c.id = m.conversation_id
        """
    )
    for column in ("shop_id", "channel_provider", "channel_account_id"):
        op.alter_column("messages", column, nullable=False)
    for column in (
        "shop_id",
        "customer_id",
        "channel_provider",
        "channel_account_id",
        "external_message_id",
        "external_update_id",
    ):
        op.create_index(op.f(f"ix_messages_{column}"), "messages", [column])


def downgrade() -> None:
    for column in (
        "external_update_id",
        "external_message_id",
        "channel_account_id",
        "channel_provider",
        "customer_id",
        "shop_id",
    ):
        op.drop_index(op.f(f"ix_messages_{column}"), table_name="messages")
    for constraint in (
        "messages_channel_account_id_fkey",
        "messages_customer_id_fkey",
        "messages_shop_id_fkey",
    ):
        op.drop_constraint(constraint, "messages", type_="foreignkey")
    for column in (
        "normalized_payload_json",
        "raw_payload_json",
        "content",
        "external_update_id",
        "external_message_id",
        "channel_account_id",
        "channel_provider",
        "customer_id",
        "shop_id",
    ):
        op.drop_column("messages", column)
    for column in ("external_thread_id", "external_conversation_id", "channel_account_id"):
        op.drop_index(op.f(f"ix_conversations_{column}"), table_name="conversations")
    op.drop_constraint("conversations_channel_account_id_fkey", "conversations", type_="foreignkey")
    op.drop_column("conversations", "external_thread_id")
    op.drop_column("conversations", "external_conversation_id")
    op.drop_column("conversations", "channel_account_id")
    op.alter_column("conversations", "instagram_account_id", nullable=False)
    op.drop_index(
        op.f("ix_channel_contact_identities_external_chat_id"),
        table_name="channel_contact_identities",
    )
    op.drop_column("channel_contact_identities", "external_chat_id")
    op.alter_column("customers", "instagram_user_id", nullable=False)
    op.create_unique_constraint(
        "uq_customers_shop_instagram_user", "customers", ["shop_id", "instagram_user_id"]
    )
    op.drop_index(op.f("ix_customers_primary_external_user_id"), table_name="customers")
    op.drop_index(op.f("ix_customers_primary_channel_provider"), table_name="customers")
    op.drop_column("customers", "primary_external_user_id")
    op.drop_column("customers", "primary_channel_provider")
    op.drop_column("customers", "email")
    op.drop_column("customers", "display_name")
