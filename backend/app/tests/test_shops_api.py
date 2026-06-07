from app.domain.enums import UserRole
from app.domain.models import Shop, ShopMember
from app.services.auth_service import AuthService


def test_list_shops_for_member(client, auth_headers, demo_shop) -> None:
    response = client.get("/api/v1/shops", headers=auth_headers)
    assert response.status_code == 200
    shops = response.json()
    assert len(shops) == 1
    assert shops[0]["slug"] == "test-shop"


def test_create_shop(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/shops",
        headers=auth_headers,
        json={"name": "New Shop", "slug": "new-shop", "default_currency": "EUR"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "New Shop"
    assert body["slug"] == "new-shop"
    assert body["default_currency"] == "EUR"


def test_get_shop_access_denied_for_non_member(client, auth_headers, db_session, demo_shop) -> None:
    outsider = AuthService.create_user(
        db_session,
        email="outsider@test.com",
        password="password123",
        full_name="Outsider",
        role=UserRole.OPERATOR,
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": outsider.email, "password": "password123"},
    )
    outsider_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get(f"/api/v1/shops/{demo_shop.id}", headers=outsider_headers)
    assert response.status_code == 403


def test_list_shop_members(client, auth_headers, demo_shop, admin_user) -> None:
    response = client.get(f"/api/v1/shops/{demo_shop.id}/members", headers=auth_headers)
    assert response.status_code == 200
    members = response.json()
    assert len(members) == 1
    assert members[0]["email"] == admin_user.email


def test_create_instagram_account(client, auth_headers, demo_shop) -> None:
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/instagram-accounts",
        headers=auth_headers,
        json={
            "ig_user_id": "12345",
            "username": "demo_store",
            "access_token": "secret-token",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "demo_store"
    assert body["ig_user_id"] == "12345"
    assert "access_token" not in body
    assert "access_token_encrypted" not in body


def test_list_instagram_accounts(client, auth_headers, demo_shop) -> None:
    client.post(
        f"/api/v1/shops/{demo_shop.id}/instagram-accounts",
        headers=auth_headers,
        json={
            "ig_user_id": "99999",
            "username": "listed_store",
            "access_token": "secret-token",
        },
    )
    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/instagram-accounts",
        headers=auth_headers,
    )
    assert response.status_code == 200
    accounts = response.json()
    assert len(accounts) == 1
    assert accounts[0]["username"] == "listed_store"
