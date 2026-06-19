"""generic catalog attributes

Revision ID: 20260613_0026
Revises: 20260612_0025
Create Date: 2026-06-13 00:00:00.000000
"""
from collections.abc import Sequence
import json
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260613_0026"
down_revision: str | None = "20260612_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts():
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)


def upgrade() -> None:
    op.create_table("product_categories",sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=True),sa.Column("name", sa.String(255), nullable=False),sa.Column("slug", sa.String(128), nullable=False),sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),sa.Column("description", sa.Text(), nullable=True),sa.Column("is_system_default", sa.Boolean(), nullable=False, server_default=sa.false()),*_ts(),sa.ForeignKeyConstraint(["parent_id"],["product_categories.id"],ondelete="SET NULL"),sa.ForeignKeyConstraint(["shop_id"],["shops.id"],ondelete="CASCADE"),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("shop_id","slug",name="uq_product_categories_shop_slug"))
    op.create_table("catalog_attribute_definitions",sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=True),sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),sa.Column("name", sa.String(255), nullable=False),sa.Column("slug", sa.String(128), nullable=False),sa.Column("data_type", sa.String(32), nullable=False, server_default="text"),sa.Column("unit", sa.String(64), nullable=True),sa.Column("is_variant_defining", sa.Boolean(), nullable=False, server_default=sa.false()),sa.Column("is_searchable", sa.Boolean(), nullable=False, server_default=sa.true()),sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),sa.Column("allowed_values_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),sa.Column("aliases_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),*_ts(),sa.ForeignKeyConstraint(["category_id"],["product_categories.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["shop_id"],["shops.id"],ondelete="CASCADE"),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("shop_id","category_id","slug",name="uq_catalog_attribute_definitions_scope_slug"))
    op.create_table("product_attributes",sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),sa.Column("attribute_definition_id", postgresql.UUID(as_uuid=True), nullable=False),sa.Column("value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),sa.Column("normalized_value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),*_ts(),sa.ForeignKeyConstraint(["attribute_definition_id"],["catalog_attribute_definitions.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["product_id"],["products.id"],ondelete="CASCADE"),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("product_id","attribute_definition_id",name="uq_product_attributes_product_definition"))
    op.create_table("variant_attributes",sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=False),sa.Column("attribute_definition_id", postgresql.UUID(as_uuid=True), nullable=False),sa.Column("value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),sa.Column("normalized_value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),*_ts(),sa.ForeignKeyConstraint(["attribute_definition_id"],["catalog_attribute_definitions.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["product_variant_id"],["product_variants.id"],ondelete="CASCADE"),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("product_variant_id","attribute_definition_id",name="uq_variant_attributes_variant_definition"))
    op.create_table("attribute_aliases",sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),sa.Column("shop_id", postgresql.UUID(as_uuid=True), nullable=True),sa.Column("attribute_definition_id", postgresql.UUID(as_uuid=True), nullable=False),sa.Column("raw_value", sa.String(128), nullable=False),sa.Column("normalized_value", sa.String(128), nullable=False),sa.Column("language", sa.String(16), nullable=True),sa.Column("confidence", sa.Numeric(4,3), nullable=False, server_default="1"),sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),*_ts(),sa.ForeignKeyConstraint(["attribute_definition_id"],["catalog_attribute_definitions.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["shop_id"],["shops.id"],ondelete="CASCADE"),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("shop_id","attribute_definition_id","raw_value","language",name="uq_attribute_aliases_scope_raw_language"))
    op.create_table("category_presets",sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),sa.Column("name", sa.String(255), nullable=False),sa.Column("slug", sa.String(128), nullable=False),sa.Column("description", sa.Text(), nullable=False, server_default=""),sa.Column("preset_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),sa.Column("is_system_default", sa.Boolean(), nullable=False, server_default=sa.true()),*_ts(),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("slug",name="uq_category_presets_slug"))
    for table in ["product_categories","catalog_attribute_definitions","product_attributes","variant_attributes","attribute_aliases","category_presets"]:
        for col in ["created_at","updated_at"]:
            op.create_index(op.f(f"ix_{table}_{col}"), table, [col])
    for slug,name,attrs in [("clothing-apparel","Clothing and apparel",["color","size","material","fit","gender","season"]),("shoes-bags","Shoes and bags",["size","color","material","style"]),("electronics","Electronics",["model","storage","ram","color","warranty","region","voltage"]),("cosmetics-beauty","Cosmetics and beauty",["shade","skin_type","volume","scent","ingredients","expiration_date"]),("home-decoration","Home and decoration",["color","dimensions","material","weight","style"]),("food-grocery","Food and grocery",["flavor","weight","pack_count","expiration_date","storage_condition"]),("books-media","Books and media",["author","language","edition","format","publisher"]),("digital-products","Digital products",["platform","license_type","duration","delivery_method"]),("general-product","General product",["color","model","size","weight","warranty"])]:
        op.execute(sa.text("INSERT INTO category_presets (id,name,slug,description,preset_json,is_system_default) VALUES (gen_random_uuid(),:name,:slug,:desc,CAST(:preset AS jsonb), true)").bindparams(name=name,slug=slug,desc=f"Default attributes for {name} shops.",preset=json.dumps({"attributes": attrs})))


def downgrade() -> None:
    for table in ["category_presets","attribute_aliases","variant_attributes","product_attributes","catalog_attribute_definitions","product_categories"]:
        op.drop_table(table)
