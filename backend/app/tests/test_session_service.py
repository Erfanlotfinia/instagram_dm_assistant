from __future__ import annotations

from app.domain.models import RefreshSession
from app.services.session_service import SessionService


def _active_sessions(db_session, family_id) -> list[RefreshSession]:
    return (
        db_session.query(RefreshSession)
        .filter_by(family_id=family_id, revoked_at=None)
        .all()
    )


def test_create_assigns_family_id(db_session, admin_user) -> None:
    service = SessionService(db_session)
    session, _token = service.create(admin_user.id, "test-agent", "127.0.0.1")

    assert session.family_id is not None
    assert session.parent_session_id is None


def test_rotate_preserves_family_id_and_sets_parent(db_session, admin_user) -> None:
    service = SessionService(db_session)
    session, token = service.create(admin_user.id, "test-agent", "127.0.0.1")
    original_family_id = session.family_id
    original_session_id = session.session_id

    rotated = service.rotate(token, "test-agent", "127.0.0.1")
    assert rotated is not None
    new_session, _new_token = rotated

    assert new_session.family_id == original_family_id
    assert new_session.parent_session_id == original_session_id
    db_session.refresh(session)
    assert session.revoked_at is not None


def test_second_rotation_keeps_same_family_id(db_session, admin_user) -> None:
    service = SessionService(db_session)
    _session, token1 = service.create(admin_user.id, "test-agent", "127.0.0.1")
    family_id = _session.family_id

    _session2, token2 = service.rotate(token1, "test-agent", "127.0.0.1")  # type: ignore[misc]
    rotated = service.rotate(token2, "test-agent", "127.0.0.1")
    assert rotated is not None
    third_session, _token3 = rotated

    assert third_session.family_id == family_id


def test_reusing_old_refresh_token_returns_none(db_session, admin_user) -> None:
    service = SessionService(db_session)
    _session, token1 = service.create(admin_user.id, "test-agent", "127.0.0.1")
    _session2, _token2 = service.rotate(token1, "test-agent", "127.0.0.1")  # type: ignore[misc]

    assert service.rotate(token1, "test-agent", "127.0.0.1") is None


def test_reuse_revokes_entire_active_family(db_session, admin_user) -> None:
    service = SessionService(db_session)
    session, token1 = service.create(admin_user.id, "test-agent", "127.0.0.1")
    _session2, token2 = service.rotate(token1, "test-agent", "127.0.0.1")  # type: ignore[misc]

    assert service.rotate(token1, "test-agent", "127.0.0.1") is None
    assert _active_sessions(db_session, session.family_id) == []


def test_refresh_after_family_revocation_fails(db_session, admin_user) -> None:
    service = SessionService(db_session)
    _session, token1 = service.create(admin_user.id, "test-agent", "127.0.0.1")
    _session2, token2 = service.rotate(token1, "test-agent", "127.0.0.1")  # type: ignore[misc]

    service.rotate(token1, "test-agent", "127.0.0.1")
    assert service.rotate(token2, "test-agent", "127.0.0.1") is None


def test_logout_revokes_only_current_session(db_session, admin_user) -> None:
    service = SessionService(db_session)
    session1, token1 = service.create(admin_user.id, "test-agent", "127.0.0.1")
    session2, token2 = service.create(admin_user.id, "test-agent", "127.0.0.1")

    service.revoke_by_token(token1)

    db_session.refresh(session1)
    db_session.refresh(session2)
    assert session1.revoked_at is not None
    assert session2.revoked_at is None
    assert session1.family_id != session2.family_id

    assert service.rotate(token2, "test-agent", "127.0.0.1") is not None
