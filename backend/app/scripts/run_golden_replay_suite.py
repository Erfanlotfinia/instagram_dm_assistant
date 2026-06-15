#!/usr/bin/env python3
"""Run golden replay scenario pack for CI certification."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.domain  # noqa: F401
from app.core.config import get_settings
from app.core.security import encrypt_secret
from app.domain.enums import InstagramAccountStatus, UserRole
from app.domain.models import InstagramAccount, Shop, ShopMember
from app.repositories.policy_version_repository import PolicyVersionRepository
from app.schemas.replay import ReplayRunRequest, ReplayScenarioInput
from app.scripts._db_bootstrap import ensure_database_schema
from app.services.auth_service import AuthService
from app.services.policy_engine import DEFAULT_POLICY_CONFIG
from app.services.replay_engine import ReplayEngine

FIXTURE = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "golden_replay_scenarios.json"
)


def main() -> int:
    ensure_database_schema()
    database_url = get_settings().database_url
    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    scenarios = json.loads(FIXTURE.read_text(encoding="utf-8"))

    with SessionLocal() as db:
        shop = Shop(name="Golden Replay Shop", slug=f"golden-replay-{uuid4().hex[:8]}")
        db.add(shop)
        db.flush()
        user = AuthService.create_user(
            db,
            email=f"golden-{uuid4().hex[:8]}@test.com",
            password="password123",
            full_name="Golden Runner",
            role=UserRole.OWNER,
        )
        db.add(ShopMember(shop_id=shop.id, user_id=user.id, role=UserRole.OWNER))
        db.add(
            InstagramAccount(
                shop_id=shop.id,
                ig_user_id="golden-ig",
                username="golden_shop",
                access_token_encrypted=encrypt_secret("token"),
                status=InstagramAccountStatus.CONNECTED,
            )
        )
        PolicyVersionRepository(db).ensure_default(
            shop.id,
            version=get_settings().default_policy_version,
            name="Golden default policy",
            config_json=DEFAULT_POLICY_CONFIG,
        )
        db.commit()

        payload = ReplayRunRequest(
            label="golden-ci-run",
            scenarios=[ReplayScenarioInput(**scenario) for scenario in scenarios],
        )
        run = ReplayEngine(db).run(shop.id, payload, user)
        report = {
            "run_id": str(run.id),
            "status": run.status.value,
            "passed_items": run.passed_items,
            "failed_items": run.failed_items,
            "total_items": run.total_items,
            "pass_rate": run.passed_items / max(run.total_items, 1),
        }
        print(json.dumps(report, indent=2))
        return 0 if run.failed_items == 0 and run.status.value == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
