"""Ensure the default local admin user exists.

Usage:
    python -m app.scripts.ensure_admin

Configure via .env: DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_NAME
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.domain.enums import UserRole
from app.domain.models import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


def ensure_default_admin(db: Session | None = None, settings: Settings | None = None) -> User:
    """Create the default admin user if missing. Safe to run on every startup."""
    config = settings or get_settings()
    admin_email = config.default_admin_email.lower()
    owns_session = db is None
    session = db or SessionLocal()
    try:
        users = UserRepository(session)
        admin = users.get_by_email(admin_email)
        if admin is None:
            admin = AuthService.create_user(
                session,
                email=admin_email,
                password=config.default_admin_password,
                full_name=config.default_admin_name,
                role=UserRole.OWNER,
            )
            logger.info("Created admin user: %s", admin_email)
        else:
            logger.info("Admin user already exists: %s", admin_email)
        if owns_session:
            session.commit()
        return admin
    except Exception:
        if owns_session:
            session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ensure_default_admin()
