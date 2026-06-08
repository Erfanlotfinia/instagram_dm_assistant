from decimal import Decimal

from app.domain.models import Product, UnavailableDemandLog


def test_analytics_unavailable_demand_from_logs(client, auth_headers, db_session, demo_shop) -> None:
    product = Product(shop_id=demo_shop.id, title="Dress", base_price=Decimal("79.99"), currency="USD")
    db_session.add(product)
    db_session.flush()
    db_session.add(
        UnavailableDemandLog(
            shop_id=demo_shop.id,
            product_id=product.id,
            requested_color_raw="red",
            requested_color_normalized="red",
            requested_size_raw="M",
            requested_size_normalized="M",
            requested_quantity=1,
            reason="out_of_stock",
            estimated_lost_revenue=Decimal("79.99"),
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/analytics/unavailable-demand",
        headers=auth_headers,
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["requested_color"] == "red"
    assert rows[0]["requested_size"] == "M"
    assert rows[0]["count"] == 1
    assert Decimal(rows[0]["lost_revenue_estimate"]) == Decimal("79.99")


def test_analytics_stock_demand_from_logs(client, auth_headers, db_session, demo_shop) -> None:
    product = Product(shop_id=demo_shop.id, title="Hoodie", base_price=Decimal("59.99"), currency="USD")
    db_session.add(product)
    db_session.flush()
    db_session.add_all(
        [
            UnavailableDemandLog(
                shop_id=demo_shop.id,
                product_id=product.id,
                requested_color_normalized="yellow",
                requested_size_normalized="L",
                requested_quantity=1,
                reason="variant_not_found",
            ),
            UnavailableDemandLog(
                shop_id=demo_shop.id,
                product_id=product.id,
                requested_color_normalized="yellow",
                requested_size_normalized="L",
                requested_quantity=1,
                reason="out_of_stock",
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/analytics/stock-demand",
        headers=auth_headers,
    )
    assert response.status_code == 200
    rows = response.json()
    color_row = next(row for row in rows if row["type"] == "color" and row["value"] == "yellow")
    size_row = next(row for row in rows if row["type"] == "size" and row["value"] == "L")
    assert color_row["requests"] == 2
    assert size_row["requests"] == 2
