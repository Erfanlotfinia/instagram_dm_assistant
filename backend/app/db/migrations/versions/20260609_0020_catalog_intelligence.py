"""catalog intelligence foundation

Revision ID: 20260609_0020
Revises: 20260609_0019
Create Date: 2026-06-09 20:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260609_0020"
down_revision: str | None = "20260609_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

catalog_import_job_status = postgresql.ENUM(
    "pending", "running", "paused", "completed", "failed",
    name="catalog_import_job_status", create_type=False,
)
catalog_alias_source = postgresql.ENUM(
    "manual", "import", "generated", "operator_feedback",
    name="catalog_alias_source", create_type=False,
)
variant_alias_type = postgresql.ENUM(
    "color", "size", "sku", "combined",
    name="variant_alias_type", create_type=False,
)
resolver_trace_type = postgresql.ENUM(
    "product", "variant",
    name="resolver_trace_type", create_type=False,
)
resolver_confidence_band = postgresql.ENUM(
    "low", "medium", "high",
    name="resolver_confidence_band", create_type=False,
)
resolver_feedback_action = postgresql.ENUM(
    "accept_ai", "correct_product", "correct_variant", "taxonomy_issue",
    name="resolver_feedback_action", create_type=False,
)


def upgrade() -> None:
    catalog_import_job_status.create(op.get_bind(), checkfirst=True)
    catalog_alias_source.create(op.get_bind(), checkfirst=True)
    variant_alias_type.create(op.get_bind(), checkfirst=True)
    resolver_trace_type.create(op.get_bind(), checkfirst=True)
    resolver_confidence_band.create(op.get_bind(), checkfirst=True)
    resolver_feedback_action.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "products_normalized",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("normalized_title", sa.String(512), nullable=False),
        sa.Column("brand", sa.String(128), nullable=True),
        sa.Column("color", sa.String(128), nullable=True),
        sa.Column("size", sa.String(64), nullable=True),
        sa.Column("material", sa.String(128), nullable=True),
        sa.Column("gender", sa.String(32), nullable=True),
        sa.Column("collection", sa.String(128), nullable=True),
        sa.Column("synonym_candidates", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("qdrant_point_id", sa.String(128), nullable=True),
        sa.Column("qdrant_variant_point_ids", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("embedding_model", sa.String(128), nullable=True),
        sa.Column("embedding_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("dense_vector_dim", sa.Integer(), nullable=True),
        sa.Column("last_normalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("product_id", name="uq_products_normalized_product_id"),
    )
    op.create_index("ix_products_normalized_shop_id", "products_normalized", ["shop_id"])
    op.create_index("ix_products_normalized_product_id", "products_normalized", ["product_id"])
    op.create_index("ix_products_normalized_brand", "products_normalized", ["brand"])
    op.create_index("ix_products_normalized_gender", "products_normalized", ["gender"])
    op.create_index("ix_products_normalized_collection", "products_normalized", ["collection"])

    op.create_table(
        "product_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("normalized_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products_normalized.id", ondelete="SET NULL"), nullable=True),
        sa.Column("alias_text", sa.String(512), nullable=False),
        sa.Column("language", sa.String(16), nullable=False, server_default="und"),
        sa.Column("source", catalog_alias_source, nullable=False, server_default="manual"),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="1.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("shop_id", "alias_text", name="uq_product_aliases_shop_alias"),
    )
    op.create_index("ix_product_aliases_shop_id", "product_aliases", ["shop_id"])
    op.create_index("ix_product_aliases_product_id", "product_aliases", ["product_id"])
    op.create_index("ix_product_aliases_alias_text", "product_aliases", ["alias_text"])

    op.create_table(
        "variant_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias_text", sa.String(256), nullable=False),
        sa.Column("alias_type", variant_alias_type, nullable=False, server_default="combined"),
        sa.Column("language", sa.String(16), nullable=False, server_default="und"),
        sa.Column("source", catalog_alias_source, nullable=False, server_default="manual"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("shop_id", "variant_id", "alias_text", name="uq_variant_aliases_shop_variant_alias"),
    )
    op.create_index("ix_variant_aliases_shop_id", "variant_aliases", ["shop_id"])
    op.create_index("ix_variant_aliases_variant_id", "variant_aliases", ["variant_id"])
    op.create_index("ix_variant_aliases_alias_text", "variant_aliases", ["alias_text"])

    op.create_table(
        "catalog_import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", catalog_import_job_status, nullable=False, server_default="pending"),
        sa.Column("source_format", sa.String(32), nullable=False, server_default="json"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checkpoint", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_catalog_import_jobs_shop_id", "catalog_import_jobs", ["shop_id"])
    op.create_index("ix_catalog_import_jobs_status", "catalog_import_jobs", ["status"])

    op.create_table(
        "resolver_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trace_type", resolver_trace_type, nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("input_payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("top_candidates", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("matched_aliases", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("rules_fired", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("missing_slots", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("confidence_band", resolver_confidence_band, nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("qdrant_query_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_resolver_traces_shop_id", "resolver_traces", ["shop_id"])
    op.create_index("ix_resolver_traces_trace_type", "resolver_traces", ["trace_type"])
    op.create_index("ix_resolver_traces_confidence_band", "resolver_traces", ["confidence_band"])
    op.create_index("ix_resolver_traces_created_at", "resolver_traces", ["created_at"])

    op.create_table(
        "resolver_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resolver_traces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", resolver_feedback_action, nullable=False),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("corrected_product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True),
        sa.Column("original_variant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("corrected_variant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_resolver_feedback_shop_id", "resolver_feedback", ["shop_id"])
    op.create_index("ix_resolver_feedback_trace_id", "resolver_feedback", ["trace_id"])
    op.create_index("ix_resolver_feedback_action", "resolver_feedback", ["action"])

    op.create_table(
        "brand_size_maps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand", sa.String(128), nullable=False),
        sa.Column("raw_size", sa.String(64), nullable=False),
        sa.Column("normalized_size", sa.String(64), nullable=False),
        sa.Column("gender", sa.String(32), nullable=True),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("shop_id", "brand", "raw_size", name="uq_brand_size_maps_shop_brand_raw"),
    )
    op.create_index("ix_brand_size_maps_shop_id", "brand_size_maps", ["shop_id"])
    op.create_index("ix_brand_size_maps_brand", "brand_size_maps", ["brand"])

    op.create_table(
        "media_product_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shop_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shops.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_id", sa.String(256), nullable=False),
        sa.Column("media_url", sa.String(2048), nullable=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("link_source", sa.String(64), nullable=False, server_default="manual"),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="1.0"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("shop_id", "media_id", "product_id", name="uq_media_product_links_shop_media_product"),
    )
    op.create_index("ix_media_product_links_shop_id", "media_product_links", ["shop_id"])
    op.create_index("ix_media_product_links_media_id", "media_product_links", ["media_id"])
    op.create_index("ix_media_product_links_product_id", "media_product_links", ["product_id"])


def downgrade() -> None:
    op.drop_table("media_product_links")
    op.drop_table("brand_size_maps")
    op.drop_table("resolver_feedback")
    op.drop_table("resolver_traces")
    op.drop_table("catalog_import_jobs")
    op.drop_table("variant_aliases")
    op.drop_table("product_aliases")
    op.drop_table("products_normalized")

    resolver_feedback_action.drop(op.get_bind(), checkfirst=True)
    resolver_confidence_band.drop(op.get_bind(), checkfirst=True)
    resolver_trace_type.drop(op.get_bind(), checkfirst=True)
    variant_alias_type.drop(op.get_bind(), checkfirst=True)
    catalog_alias_source.drop(op.get_bind(), checkfirst=True)
    catalog_import_job_status.drop(op.get_bind(), checkfirst=True)
