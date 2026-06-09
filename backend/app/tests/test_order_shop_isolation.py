"""Multi-tenant order isolation tests."""

from app.domain.enums import ShopStatus, UserRole
from app.domain.models import Shop, ShopMember
from app.services.auth_service import AuthService
from app.tests.fixtures.orders import seed_draft_order, seed_order_flow_data


def test_cannot_access_other_shop_order(client, admin_user, demo_shop, db_session, order_product) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=order_product["product"],
        variant=order_product["variant"],
    )
    db_session.commit()

    other_shop = Shop(name="Other Shop", slug="other-shop-iso", status=ShopStatus.ACTIVE)
    db_session.add(other_shop)
    db_session.flush()
    other_user = AuthService.create_user(
        db_session,
        email="isolated@test.com",
        password="password123",
        full_name="Isolated User",
        role=UserRole.OWNER,
    )
    db_session.add(ShopMember(shop_id=other_shop.id, user_id=other_user.id, role=UserRole.OWNER))
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "isolated@test.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get(f"/api/v1/orders/{order.id}", headers=headers)
    assert response.status_code in {403, 404}
