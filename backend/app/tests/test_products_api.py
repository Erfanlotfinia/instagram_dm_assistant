from decimal import Decimal

import pytest

from app.domain.enums import UserRole
from app.services.auth_service import AuthService


@pytest.fixture()
def product_payload() -> dict:
    return {
        "title": "Summer Dress",
        "description": "Light cotton dress",
        "base_price": "49.99",
        "currency": "USD",
    }


@pytest.fixture()
def created_product(client, auth_headers, demo_shop, product_payload):
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/products",
        headers=auth_headers,
        json=product_payload,
    )
    assert response.status_code == 201
    return response.json()


def test_create_product(client, auth_headers, demo_shop, product_payload) -> None:
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/products",
        headers=auth_headers,
        json=product_payload,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Summer Dress"
    assert body["base_price"] == "49.99"
    assert body["currency"] == "USD"
    assert body["status"] == "active"


def test_list_products(client, auth_headers, demo_shop, created_product) -> None:
    response = client.get(f"/api/v1/shops/{demo_shop.id}/products", headers=auth_headers)
    assert response.status_code == 200
    products = response.json()
    assert len(products) == 1
    assert products[0]["id"] == created_product["id"]


def test_get_product(client, auth_headers, demo_shop, created_product) -> None:
    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/products/{created_product['id']}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Summer Dress"


def test_update_product(client, auth_headers, demo_shop, created_product) -> None:
    response = client.patch(
        f"/api/v1/shops/{demo_shop.id}/products/{created_product['id']}",
        headers=auth_headers,
        json={"title": "Updated Dress", "status": "inactive"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Updated Dress"
    assert body["status"] == "inactive"


def test_delete_product(client, auth_headers, demo_shop, created_product) -> None:
    response = client.delete(
        f"/api/v1/shops/{demo_shop.id}/products/{created_product['id']}",
        headers=auth_headers,
    )
    assert response.status_code == 204

    listing = client.get(f"/api/v1/shops/{demo_shop.id}/products", headers=auth_headers)
    assert listing.json() == []


def test_product_access_denied_for_non_member(client, auth_headers, db_session, demo_shop, created_product) -> None:
    outsider = AuthService.create_user(
        db_session,
        email="product-outsider@test.com",
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
        f"/api/v1/shops/{demo_shop.id}/products/{created_product['id']}",
        headers=outsider_headers,
    )
    assert response.status_code == 403
