from uuid import uuid4

import pytest
from sqlalchemy import select

from app.domain.enums import FailedJobStatus, UserRole
from app.domain.models import FailedJob, ShopMember
from app.services.auth_service import AuthService


@pytest.fixture()
def operator_user(db_session, demo_shop):
    user = AuthService.create_user(
        db_session,
        email="operator@test.com",
        password="password123",
        full_name="Operator",
        role=UserRole.OPERATOR,
    )
    db_session.add(
        ShopMember(
            shop_id=demo_shop.id,
            user_id=user.id,
            role=UserRole.OPERATOR,
        )
    )
    db_session.commit()
    return user


@pytest.fixture()
def operator_headers(client, operator_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "operator@test.com", "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_operator_cannot_list_failed_jobs(client, operator_headers, demo_shop, db_session) -> None:
    db_session.add(
        FailedJob(
            shop_id=demo_shop.id,
            queue_name="channel.message.received",
            job_type="message_received",
            payload={"shop_id": str(demo_shop.id), "access_token": "secret-token"},
            error_message="boom",
            status=FailedJobStatus.FAILED,
            resolved=False,
        )
    )
    db_session.commit()

    response = client.get(f"/api/v1/shops/{demo_shop.id}/failed-jobs", headers=operator_headers)
    assert response.status_code == 403


def test_admin_sees_redacted_payload(client, auth_headers, demo_shop, db_session) -> None:
    db_session.add(
        FailedJob(
            shop_id=demo_shop.id,
            queue_name="channel.message.received",
            job_type="message_received",
            payload={
                "shop_id": str(demo_shop.id),
                "access_token": "super-secret-token",
                "email": "user@example.com",
                "phone": "09121234567",
            },
            error_message="boom",
            status=FailedJobStatus.FAILED,
            resolved=False,
        )
    )
    db_session.commit()

    response = client.get(f"/api/v1/shops/{demo_shop.id}/failed-jobs", headers=auth_headers)
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert "redacted_payload" in item
    assert "payload" not in item
    serialized = str(item["redacted_payload"])
    assert "super-secret-token" not in serialized
    assert "user@example.com" not in serialized


def test_cross_shop_failed_job_not_visible(client, auth_headers, db_session, demo_shop) -> None:
    from app.domain.models import Shop

    other_shop = Shop(name="Other", slug="other-shop")
    db_session.add(other_shop)
    db_session.flush()
    job = FailedJob(
        shop_id=other_shop.id,
        queue_name="channel.message.received",
        job_type="message_received",
        payload={"shop_id": str(other_shop.id)},
        error_message="other",
        status=FailedJobStatus.FAILED,
        resolved=False,
    )
    db_session.add(job)
    db_session.commit()

    response = client.get(f"/api/v1/shops/{other_shop.id}/failed-jobs", headers=auth_headers)
    assert response.status_code == 403


def test_legacy_failed_jobs_endpoint_gone(client, auth_headers) -> None:
    response = client.get("/api/v1/jobs/failed", headers=auth_headers)
    assert response.status_code == 410
