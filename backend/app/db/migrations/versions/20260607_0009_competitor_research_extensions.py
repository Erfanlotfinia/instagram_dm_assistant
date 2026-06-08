"""competitor research extensions

Revision ID: 20260607_0009
Revises: 20260607_0008
Create Date: 2026-06-07
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260607_0009"
down_revision = "20260607_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    trigger_source_type = postgresql.ENUM(
        "comment", "story_reply", "reel_comment", "direct_dm", "ad_comment",
        name="trigger_source_type",
        create_type=False,
    )
    trigger_source_type.create(bind, checkfirst=True)
    selling_style = postgresql.ENUM(
        "educational", "balanced", "promotional",
        name="selling_style",
        create_type=False,
    )
    selling_style.create(bind, checkfirst=True)
    op.execute("ALTER TYPE message_channel ADD VALUE IF NOT EXISTS 'whatsapp'")
    op.execute("ALTER TYPE message_channel ADD VALUE IF NOT EXISTS 'telegram'")
    op.execute("ALTER TYPE message_channel ADD VALUE IF NOT EXISTS 'web_chat'")
    op.execute("ALTER TYPE webhook_provider ADD VALUE IF NOT EXISTS 'whatsapp'")
    op.execute("ALTER TYPE webhook_provider ADD VALUE IF NOT EXISTS 'telegram'")
    op.execute("ALTER TYPE webhook_provider ADD VALUE IF NOT EXISTS 'web_chat'")

    op.create_table(
        "raw_channel_payloads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("shop_id", sa.UUID(), nullable=True),
        sa.Column("provider", postgresql.ENUM("instagram", "whatsapp", "telegram", "web_chat", name="message_channel", create_type=False), nullable=False),
        sa.Column("external_event_id", sa.String(length=128), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raw_channel_payloads_shop_id", "raw_channel_payloads", ["shop_id"])
    op.create_index("ix_raw_channel_payloads_provider", "raw_channel_payloads", ["provider"])
    op.create_index("ix_raw_channel_payloads_external_event_id", "raw_channel_payloads", ["external_event_id"])

    op.create_table(
        "comment_to_dm_triggers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("shop_id", sa.UUID(), nullable=False),
        sa.Column("instagram_account_id", sa.UUID(), nullable=False),
        sa.Column("instagram_media_id", sa.String(length=128), nullable=True),
        sa.Column("source_type", trigger_source_type, nullable=False, server_default="comment"),
        sa.Column("keyword", sa.String(length=128), nullable=False),
        sa.Column("response_template", sa.Text(), nullable=False),
        sa.Column("target_product_id", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["instagram_account_id"], ["instagram_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shop_id", "instagram_account_id", "instagram_media_id", "source_type", "keyword", name="uq_comment_to_dm_trigger_keyword"),
    )
    for col in ["shop_id", "instagram_account_id", "instagram_media_id", "source_type", "keyword", "target_product_id", "is_active"]:
        op.create_index(f"ix_comment_to_dm_triggers_{col}", "comment_to_dm_triggers", [col])

    op.add_column("conversations", sa.Column("channel_provider", sa.String(length=32), nullable=False, server_default="instagram"))
    op.add_column("conversations", sa.Column("channel_conversation_id", sa.String(length=128), nullable=True))
    op.add_column("conversations", sa.Column("channel_customer_id", sa.String(length=128), nullable=True))
    op.add_column("conversations", sa.Column("trigger_rule_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_conversations_trigger_rule_id", "conversations", "comment_to_dm_triggers", ["trigger_rule_id"], ["id"], ondelete="SET NULL")
    for col in ["channel_provider", "channel_conversation_id", "channel_customer_id", "trigger_rule_id"]:
        op.create_index(f"ix_conversations_{col}", "conversations", [col])

    op.add_column("messages", sa.Column("channel_message_id", sa.String(length=128), nullable=True))
    op.add_column("messages", sa.Column("raw_channel_payload_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_messages_raw_channel_payload_id", "messages", "raw_channel_payloads", ["raw_channel_payload_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_messages_channel_message_id", "messages", ["channel_message_id"])
    op.create_index("ix_messages_raw_channel_payload_id", "messages", ["raw_channel_payload_id"])

    op.add_column("instagram_product_maps", sa.Column("visual_hint", sa.String(length=255), nullable=True))
    op.add_column("instagram_product_maps", sa.Column("caption_hint", sa.String(length=255), nullable=True))
    op.add_column("instagram_product_maps", sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "trigger_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("trigger_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=True),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("matched_keyword", sa.String(length=128), nullable=False),
        sa.Column("source_type", trigger_source_type, nullable=False),
        sa.Column("dm_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("paid_order_id", sa.UUID(), nullable=True),
        sa.Column("revenue_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["paid_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["trigger_id"], ["comment_to_dm_triggers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ["trigger_id", "conversation_id", "customer_id", "paid_order_id", "created_at"]:
        op.create_index(f"ix_trigger_events_{col}", "trigger_events", [col])

    op.create_table("color_aliases", sa.Column("id", sa.UUID(), nullable=False), sa.Column("shop_id", sa.UUID(), nullable=True), sa.Column("raw_value", sa.String(length=128), nullable=False), sa.Column("normalized_value", sa.String(length=128), nullable=False), sa.Column("language", sa.String(length=16), nullable=False, server_default="und"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("shop_id", "raw_value", "language", name="uq_color_alias_shop_raw_language"))
    op.create_table("size_aliases", sa.Column("id", sa.UUID(), nullable=False), sa.Column("shop_id", sa.UUID(), nullable=True), sa.Column("raw_value", sa.String(length=128), nullable=False), sa.Column("normalized_value", sa.String(length=128), nullable=False), sa.Column("category", sa.String(length=128), nullable=True), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("shop_id", "raw_value", "category", name="uq_size_alias_shop_raw_category"))
    op.create_table("product_size_charts", sa.Column("id", sa.UUID(), nullable=False), sa.Column("shop_id", sa.UUID(), nullable=False), sa.Column("product_id", sa.UUID(), nullable=True), sa.Column("category", sa.String(length=128), nullable=False), sa.Column("chart_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_table("unavailable_demand", sa.Column("id", sa.UUID(), nullable=False), sa.Column("shop_id", sa.UUID(), nullable=False), sa.Column("product_id", sa.UUID(), nullable=True), sa.Column("requested_color", sa.String(length=128), nullable=True), sa.Column("requested_size", sa.String(length=128), nullable=True), sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"), sa.Column("lost_revenue_estimate", sa.Numeric(12, 2), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))

    op.create_table(
        "agent_decision_traces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=True),
        sa.Column("agent_run_id", sa.UUID(), nullable=True),
        sa.Column("intent", sa.String(length=128), nullable=True),
        sa.Column("extracted_slots", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("product_candidates", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("selected_product_id", sa.UUID(), nullable=True),
        sa.Column("variant_resolution", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("inventory_result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("order_action", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("next_state", sa.String(length=128), nullable=False),
        sa.Column("outbound_message_id", sa.UUID(), nullable=True),
        sa.Column("auto_send_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("human_handoff_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reasoning_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["outbound_message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["selected_product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ["conversation_id", "message_id", "agent_run_id", "intent", "selected_product_id", "outbound_message_id", "created_at"]:
        op.create_index(f"ix_agent_decision_traces_{col}", "agent_decision_traces", [col])

    op.create_table(
        "shop_agent_settings",
        sa.Column("shop_id", sa.UUID(), nullable=False),
        sa.Column("auto_send_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("preview_required_for_low_confidence", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("preview_required_for_first_order", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("preview_required_for_high_value_order", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("confidence_threshold_intent", sa.Numeric(5, 4), nullable=False, server_default="0.75"),
        sa.Column("confidence_threshold_product", sa.Numeric(5, 4), nullable=False, server_default="0.80"),
        sa.Column("confidence_threshold_variant", sa.Numeric(5, 4), nullable=False, server_default="0.85"),
        sa.Column("confidence_threshold_address", sa.Numeric(5, 4), nullable=False, server_default="0.80"),
        sa.Column("high_value_order_threshold", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("brand_voice", sa.Text(), nullable=True),
        sa.Column("selling_style", selling_style, nullable=False, server_default="balanced"),
        sa.Column("discount_policy_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("handoff_policy_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("shop_id"),
    )


def downgrade() -> None:
    op.drop_table("shop_agent_settings")
    op.drop_table("agent_decision_traces")
    op.drop_table("unavailable_demand")
    op.drop_table("product_size_charts")
    op.drop_table("size_aliases")
    op.drop_table("color_aliases")
    op.drop_table("trigger_events")
    op.drop_column("instagram_product_maps", "is_primary")
    op.drop_column("instagram_product_maps", "caption_hint")
    op.drop_column("instagram_product_maps", "visual_hint")
    op.drop_index("ix_messages_raw_channel_payload_id", table_name="messages")
    op.drop_index("ix_messages_channel_message_id", table_name="messages")
    op.drop_constraint("fk_messages_raw_channel_payload_id", "messages", type_="foreignkey")
    op.drop_column("messages", "raw_channel_payload_id")
    op.drop_column("messages", "channel_message_id")
    for col in ["trigger_rule_id", "channel_customer_id", "channel_conversation_id", "channel_provider"]:
        op.drop_index(f"ix_conversations_{col}", table_name="conversations")
    op.drop_constraint("fk_conversations_trigger_rule_id", "conversations", type_="foreignkey")
    op.drop_column("conversations", "trigger_rule_id")
    op.drop_column("conversations", "channel_customer_id")
    op.drop_column("conversations", "channel_conversation_id")
    op.drop_column("conversations", "channel_provider")
    op.drop_table("comment_to_dm_triggers")
    op.drop_table("raw_channel_payloads")
    op.execute("DROP TYPE IF EXISTS selling_style")
    op.execute("DROP TYPE IF EXISTS trigger_source_type")
