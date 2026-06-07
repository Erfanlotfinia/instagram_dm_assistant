def test_login_success(client, admin_user) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


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


def test_protected_shops_route_requires_auth(client) -> None:
    response = client.get("/api/v1/shops")
    assert response.status_code == 401
