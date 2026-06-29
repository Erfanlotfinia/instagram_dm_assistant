def test_login_success(client, admin_user) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["csrf_token"]


def test_cookie_session_requires_csrf_header(client, admin_user) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "password123"},
    )
    assert login.status_code == 200
    csrf_token = login.json()["csrf_token"]
    cookies = login.cookies

    blocked = client.patch(
        "/api/v1/auth/me",
        cookies=cookies,
        json={"full_name": "Blocked Update"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "CSRF validation failed"

    allowed = client.patch(
        "/api/v1/auth/me",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf_token},
        json={"full_name": "Allowed Update"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["full_name"] == "Allowed Update"


def test_csrf_bootstrap_endpoint(client, admin_user) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "password123"},
    )
    assert login.status_code == 200
    cookies = login.cookies
    csrf_token = login.json()["csrf_token"]

    response = client.get("/api/v1/auth/csrf", cookies=cookies)
    assert response.status_code == 200
    assert response.json()["csrf_token"] == csrf_token


def test_login_invalid_credentials(client, admin_user) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_me_requires_auth(client) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, auth_headers, admin_user) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@test.com"
    assert body["full_name"] == "Test Admin"
    assert "password_hash" not in body


def test_update_me_updates_full_name(client, auth_headers, admin_user) -> None:
    response = client.patch(
        "/api/v1/auth/me",
        headers=auth_headers,
        json={"full_name": "Updated Admin"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Updated Admin"

    me_response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_response.json()["full_name"] == "Updated Admin"


def test_change_password_success(client, auth_headers, admin_user) -> None:
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"current_password": "password123", "new_password": "newpassword123"},
    )
    assert response.status_code == 204

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "newpassword123"},
    )
    assert login_response.status_code == 200


def test_change_password_rejects_wrong_current_password(client, auth_headers, admin_user) -> None:
    response = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"current_password": "wrong-password", "new_password": "newpassword123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect"


def test_protected_shops_route_requires_auth(client) -> None:
    response = client.get("/api/v1/shops")
    assert response.status_code == 401
