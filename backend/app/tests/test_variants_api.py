from decimal import Decimal

import pytest

from app.domain.enums import UserRole
from app.services.auth_service import AuthService


@pytest.fixture()
def product(client, auth_headers, demo_shop):
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/products",
        headers=auth_headers,
        json={"title": "T-Shirt", "base_price": "29.99", "currency": "USD"},
    )
    return response.json()


@pytest.fixture()
def variant_payload() -> dict:
    return {
        "color": "Blue",
        "size": "M",
        "sku": "TSH-BLU-M",
        "price": "29.99",
        "stock_quantity": 10,
    }


def test_create_variant(client, auth_headers, demo_shop, product, variant_payload) -> None:
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/products/{product['id']}/variants",
        headers=auth_headers,
        json=variant_payload,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["sku"] == "TSH-BLU-M"
    assert body["stock_quantity"] == 10
    assert body["reserved_quantity"] == 0
    assert body["available_stock"] == 10


def test_list_variants(client, auth_headers, demo_shop, product, variant_payload) -> None:
    client.post(
        f"/api/v1/shops/{demo_shop.id}/products/{product['id']}/variants",
        headers=auth_headers,
        json=variant_payload,
    )
    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/products/{product['id']}/variants",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_update_variant(client, auth_headers, demo_shop, product, variant_payload) -> None:
    created = client.post(
        f"/api/v1/shops/{demo_shop.id}/products/{product['id']}/variants",
        headers=auth_headers,
        json=variant_payload,
    ).json()

    response = client.patch(
        f"/api/v1/shops/{demo_shop.id}/variants/{created['id']}",
        headers=auth_headers,
        json={"stock_quantity": 20, "color": "Navy"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stock_quantity"] == 20
    assert body["color"] == "Navy"
    assert body["available_stock"] == 20


def test_sku_unique_per_shop(client, auth_headers, demo_shop, product, variant_payload) -> None:
    client.post(
        f"/api/v1/shops/{demo_shop.id}/products/{product['id']}/variants",
        headers=auth_headers,
        json=variant_payload,
    )

    product2 = client.post(
        f"/api/v1/shops/{demo_shop.id}/products",
        headers=auth_headers,
        json={"title": "Another Shirt", "base_price": "19.99"},
    ).json()

    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/products/{product2['id']}/variants",
        headers=auth_headers,
        json={**variant_payload, "color": "Red"},
    )
    assert response.status_code == 409


def test_variant_access_denied_for_non_member(client, auth_headers, db_session, demo_shop, product, variant_payload) -> None:
    created = client.post(
        f"/api/v1/shops/{demo_shop.id}/products/{product['id']}/variants",
        headers=auth_headers,
        json=variant_payload,
    ).json()

    outsider = AuthService.create_user(
        db_session,
        email="variant-outsider@test.com",
        password="password123",
        full_name="Outsider",
        role=UserRole.OPERATOR,
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": outsider.email, "password": "password123"},
    )
    outsider_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.patch(
        f"/api/v1/shops/{demo_shop.id}/variants/{created['id']}",
        headers=outsider_headers,
        json={"stock_quantity": 5},
    )
    assert response.status_code == 403
