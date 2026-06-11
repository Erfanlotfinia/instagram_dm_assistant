from datetime import UTC, datetime
from decimal import Decimal

from app.domain.enums import OrderStatus, PaymentRecordStatus
from app.services.payment_service import PaymentService
from app.tests.fixtures.orders import seed_draft_order
from app.tests.fixtures.agent import seed_order_flow_data


def test_mock_payment_callback_marks_order_paid(client, db_session, admin_user, demo_shop, auth_headers) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    from app.domain.models import Product, ProductVariant

    product = Product(
        shop_id=demo_shop.id,
        title="Pay Test",
        base_price=Decimal("10.00"),
        currency="USD",
    )
    db_session.add(product)
    db_session.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku="PAY-001",
        price=Decimal("10.00"),
        stock_quantity=3,
    )
    db_session.add(variant)
    db_session.commit()

    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=product,
        variant=variant,
    )
    order.status = OrderStatus.DRAFT
    order.customer_confirmed_at = datetime.now(UTC)
    db_session.commit()

    from app.services.order_service import OrderService

    order_service = OrderService(db_session)
    order_service.confirm_order(demo_shop.id, order.id, admin_user)
    PaymentService(db_session).send_payment_link(demo_shop.id, order.id, admin_user)
    order = order_service.get_order_internal(order.id)
    payment = PaymentService(db_session).initiate_payment(order)

    response = client.post(
        "/api/v1/payments/mock/callback",
        json={"payment_id": str(payment.id), "status": "paid"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == OrderStatus.PAID.value
    assert body["payment_status"] == "paid"


def test_admin_mark_paid(client, db_session, admin_user, demo_shop, auth_headers) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    from app.domain.models import Product, ProductVariant

    product = Product(shop_id=demo_shop.id, title="Admin Pay", base_price=Decimal("15.00"), currency="USD")
    db_session.add(product)
    db_session.flush()
    variant = ProductVariant(product_id=product.id, sku="ADM-001", price=Decimal("15.00"), stock_quantity=2)
    db_session.add(variant)
    db_session.commit()

    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=product,
        variant=variant,
    )
    order.status = OrderStatus.DRAFT
    order.customer_confirmed_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
    db_session.commit()
    from app.services.order_service import OrderService

    OrderService(db_session).confirm_order(demo_shop.id, order.id, admin_user)
    PaymentService(db_session).send_payment_link(demo_shop.id, order.id, admin_user)

    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/orders/{order.id}/mark-paid",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == OrderStatus.PAID.value
