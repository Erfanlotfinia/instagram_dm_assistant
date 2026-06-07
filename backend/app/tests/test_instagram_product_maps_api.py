import pytest

from app.domain.enums import UserRole
from app.services.auth_service import AuthService


@pytest.fixture()
def instagram_account(client, auth_headers, demo_shop):
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/instagram-accounts",
        headers=auth_headers,
        json={
            "ig_user_id": "map-test-ig",
            "username": "map_store",
            "access_token": "secret-token",
        },
    )
    return response.json()


@pytest.fixture()
def product(client, auth_headers, demo_shop):
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/products",
        headers=auth_headers,
        json={"title": "Mapped Product", "base_price": "39.99"},
    )
    return response.json()


@pytest.fixture()
def product_map(client, auth_headers, demo_shop, instagram_account, product):
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/instagram-product-maps",
        headers=auth_headers,
        json={
            "instagram_account_id": instagram_account["id"],
            "instagram_post_url": "https://www.instagram.com/p/ABC123/",
            "instagram_media_id": "media-abc123",
            "product_id": product["id"],
            "confidence_source": "manual",
        },
    )
    return response.json()


def test_create_instagram_product_map(client, auth_headers, demo_shop, product_map) -> None:
    assert product_map["instagram_post_url"] == "https://www.instagram.com/p/ABC123"
    assert product_map["confidence_source"] == "manual"
    assert product_map["is_active"] is True


def test_list_instagram_product_maps(client, auth_headers, demo_shop, product_map) -> None:
    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/instagram-product-maps",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_update_instagram_product_map(client, auth_headers, demo_shop, product_map) -> None:
    response = client.patch(
        f"/api/v1/shops/{demo_shop.id}/instagram-product-maps/{product_map['id']}",
        headers=auth_headers,
        json={"confidence_source": "admin_confirmed", "is_active": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["confidence_source"] == "admin_confirmed"
    assert body["is_active"] is False


def test_resolve_by_post_url(client, auth_headers, demo_shop, product, product_map) -> None:
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/resolve-instagram-product",
        headers=auth_headers,
        json={"instagram_post_url": "https://www.instagram.com/p/ABC123/"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["product"]["id"] == product["id"]
    assert body["map_id"] == product_map["id"]
    assert body["confidence_source"] == "manual"


def test_resolve_by_media_id(client, auth_headers, demo_shop, product, product_map) -> None:
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/resolve-instagram-product",
        headers=auth_headers,
        json={"instagram_media_id": "media-abc123"},
    )
    assert response.status_code == 200
    assert response.json()["product"]["id"] == product["id"]


def test_resolve_returns_null_when_no_match(client, auth_headers, demo_shop) -> None:
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/resolve-instagram-product",
        headers=auth_headers,
        json={"instagram_post_url": "https://www.instagram.com/p/UNKNOWN/"},
    )
    assert response.status_code == 200
    assert response.json()["product"] is None


def test_resolve_inactive_map_returns_null(client, auth_headers, demo_shop, product_map) -> None:
    client.patch(
        f"/api/v1/shops/{demo_shop.id}/instagram-product-maps/{product_map['id']}",
        headers=auth_headers,
        json={"is_active": False},
    )
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/resolve-instagram-product",
        headers=auth_headers,
        json={"instagram_post_url": "https://www.instagram.com/p/ABC123/"},
    )
    assert response.status_code == 200
    assert response.json()["product"] is None


def test_mapping_access_denied_for_non_member(
    client, auth_headers, db_session, demo_shop, product_map
) -> None:
    outsider = AuthService.create_user(
        db_session,
        email="map-outsider@test.com",
        password="password123",
        full_name="Outsider",
        role=UserRole.OPERATOR,
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": outsider.email, "password": "password123"},
    )
    outsider_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/instagram-product-maps",
        headers=outsider_headers,
    )
    assert response.status_code == 403
