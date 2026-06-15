"""Database bootstrap helpers for standalone CI scripts."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import get_settings

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def ensure_database_schema() -> None:
    """Apply Alembic migrations before standalone scripts touch ORM tables.

    Pytest fixtures reset the shared CI database after the test suite, so scripts
    executed later in the same workflow cannot assume tables still exist even if
    an earlier CI step ran migrations. Running Alembic here is idempotent and
    keeps the scripts reliable when invoked directly against a clean database.
    """

    alembic_cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(alembic_cfg, "head")
