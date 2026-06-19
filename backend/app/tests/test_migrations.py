import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/modira_test",
)

EXPECTED_TABLES = {
    "users",
    "shops",
    "shop_members",
    "instagram_accounts",
    "customers",
    "conversations",
    "messages",
    "agent_actions",
    "webhook_events",
    "products",
    "product_variants",
    "instagram_product_maps",
    "inventory_movements",
    "alembic_version",
}


@pytest.mark.integration
def test_alembic_upgrade_creates_core_tables() -> None:
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    with engine.begin() as connection:
        connection.exec_driver_sql("DROP SCHEMA public CASCADE")
        connection.exec_driver_sql("CREATE SCHEMA public")

    command.upgrade(alembic_cfg, "head")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert EXPECTED_TABLES.issubset(tables)

    engine.dispose()
