from decimal import Decimal
from uuid import uuid4

from app.domain.enums import AgentRunStatus, FailedJobStatus, MessageDirection, MessageType, OrderPaymentStatus, OrderStatus, PaymentProvider, PaymentRecordStatus, UserRole
from app.domain.models import AdminAuditLog, AgentRun, FailedJob, Message, Order, Product, Shop, ShopMember, UnavailableDemandLog
from app.services.payment_service import PaymentService
from app.tests.fixtures.agent import build_orchestrator, create_text_message, seed_order_flow_data


def test_readiness_endpoint_shape(client) -> None:
    response = client.get("/api/v1/ready")
    assert response.status_code in {200, 503}
    body = response.json()
    assert body["status"] in {"ok", "degraded", "failed"}
    assert set(body["checks"]) == {"postgres", "redis", "rabbitmq", "qdrant", "openai_config"}
    for value in body["checks"].values():
        assert value in {"ok", "error"}
    if body["status"] == "failed":
        assert response.status_code == 503
    else:
        assert response.status_code == 200


def test_readiness_degraded_returns_200_when_postgres_ok(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.health._check_openai_config",
        lambda: {"status": "error", "detail": "OPENAI_API_KEY is not configured"},
    )
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["openai_config"] == "error"


def test_analytics_funnel_date_filter(client, auth_headers, demo_shop) -> None:
    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/analytics/funnel",
        headers=auth_headers,
        params={"date_from": "2026-01-01T00:00:00Z", "date_to": "2026-12-31T23:59:59Z"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "product_resolved_rate" in body
    assert "payment_conversion_rate" in body


def test_analytics_lost_demand(client, auth_headers, db_session, demo_shop) -> None:
    product = Product(shop_id=demo_shop.id, title="Jacket", base_price=Decimal("120.00"), currency="USD")
    db_session.add(product)
    db_session.flush()
    db_session.add(
        UnavailableDemandLog(
            shop_id=demo_shop.id,
            product_id=product.id,
            requested_color_normalized="navy",
            requested_size_normalized="M",
            requested_quantity=1,
            reason="out_of_stock",
            estimated_lost_revenue=Decimal("120.00"),
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/analytics/lost-demand",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert body["items"][0]["requested_product"] == "Jacket"
    assert body["items"][0]["reason"] == "out_of_stock"


def test_analytics_agent_performance(client, auth_headers, demo_shop) -> None:
    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/analytics/agent-performance",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "auto_sent_messages" in body
    assert "handoff_rate" in body


def test_analytics_shop_isolation(client, auth_headers, db_session, demo_shop, admin_user) -> None:
    other_shop = Shop(name="Other Shop", slug=f"other-{uuid4().hex[:8]}")
    db_session.add(other_shop)
    db_session.flush()
    db_session.add(ShopMember(shop_id=other_shop.id, user_id=admin_user.id, role=UserRole.OWNER))
    product = Product(shop_id=other_shop.id, title="Other", base_price=Decimal("10.00"), currency="USD")
    db_session.add(product)
    db_session.flush()
    db_session.add(
        UnavailableDemandLog(
            shop_id=other_shop.id,
            product_id=product.id,
            requested_color_normalized="red",
            requested_size_normalized="L",
            requested_quantity=1,
            reason="out_of_stock",
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/analytics/lost-demand",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_failed_jobs_list_includes_unscoped_jobs(client, auth_headers, db_session, demo_shop) -> None:
    scoped = FailedJob(
        shop_id=demo_shop.id,
        queue_name="instagram.message.received",
        job_type="message_received",
        payload={"shop_id": str(demo_shop.id)},
        error_message="shop scoped",
        status=FailedJobStatus.FAILED,
        resolved=False,
    )
    unscoped = FailedJob(
        shop_id=None,
        queue_name="instagram.message.received.dlq",
        job_type="message_received",
        payload={"raw": "payload"},
        error_message="orphan",
        status=FailedJobStatus.FAILED,
        resolved=False,
    )
    db_session.add_all([scoped, unscoped])
    db_session.commit()

    shop_response = client.get(f"/api/v1/shops/{demo_shop.id}/failed-jobs", headers=auth_headers)
    assert shop_response.status_code == 200
    shop_items = shop_response.json()["items"]
    assert len(shop_items) == 2
    assert {item["error_message"] for item in shop_items} == {"shop scoped", "orphan"}

    platform_response = client.get("/api/v1/failed-jobs", headers=auth_headers)
    assert platform_response.status_code == 200
    assert platform_response.json()["total"] == 2

    shop_only = client.get(f"/api/v1/failed-jobs?shop_id={demo_shop.id}", headers=auth_headers)
    assert shop_only.status_code == 200
    assert shop_only.json()["total"] == 1
    assert shop_only.json()["items"][0]["error_message"] == "shop scoped"

    unscoped_only = client.get("/api/v1/failed-jobs?unscoped_only=true", headers=auth_headers)
    assert unscoped_only.status_code == 200
    assert unscoped_only.json()["total"] == 1
    assert unscoped_only.json()["items"][0]["error_message"] == "orphan"


def test_failed_jobs_list_retry_ignore(client, auth_headers, db_session, demo_shop, monkeypatch) -> None:
    message_id = uuid4()
    conversation_id = uuid4()
    job = FailedJob(
        shop_id=demo_shop.id,
        queue_name="instagram.message.received",
        job_type="message_received",
        payload={
            "shop_id": str(demo_shop.id),
            "message_id": str(message_id),
            "conversation_id": str(conversation_id),
            "instagram_account_id": str(uuid4()),
            "customer_id": str(uuid4()),
        },
        error_message="boom",
        retry_count=3,
        max_retries=3,
        status=FailedJobStatus.FAILED,
        resolved=False,
    )
    db_session.add(job)
    db_session.commit()

    listed = client.get(f"/api/v1/shops/{demo_shop.id}/failed-jobs", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    published: list[dict] = []

    class FakePublisher:
        def publish(self, queue_name, payload, retry_count=0):
            published.append({"queue_name": queue_name, "payload": payload, "retry_count": retry_count})

        def close(self):
            return None

    monkeypatch.setattr("app.services.failed_job_service.RabbitMQPublisher", lambda settings: FakePublisher())

    retried = client.post(
        f"/api/v1/shops/{demo_shop.id}/failed-jobs/{job.id}/retry",
        headers=auth_headers,
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "retried"
    assert published

    job2 = FailedJob(
        shop_id=demo_shop.id,
        queue_name="instagram.message.received",
        job_type="message_received",
        payload={"shop_id": str(demo_shop.id)},
        error_message="still failing",
        retry_count=3,
        max_retries=3,
        status=FailedJobStatus.FAILED,
        resolved=False,
    )
    db_session.add(job2)
    db_session.commit()

    ignored = client.post(
        f"/api/v1/shops/{demo_shop.id}/failed-jobs/{job2.id}/ignore",
        headers=auth_headers,
    )
    assert ignored.status_code == 200
    assert ignored.json()["status"] == "ignored"

    audit_actions = {
        row.action
        for row in db_session.query(AdminAuditLog).filter(AdminAuditLog.shop_id == demo_shop.id).all()
    }
    assert "failed_job_retried" in audit_actions
    assert "failed_job_ignored" in audit_actions


def test_failed_jobs_retry_rejects_malformed_payload(client, auth_headers, db_session, demo_shop) -> None:
    job = FailedJob(
        shop_id=demo_shop.id,
        queue_name="instagram.message.received.dlq",
        job_type="message_received",
        payload={"raw": "malformed-worker-payload", "retry_count": 3},
        error_message="Invalid message_received job payload",
        retry_count=3,
        max_retries=3,
        status=FailedJobStatus.FAILED,
        resolved=False,
    )
    db_session.add(job)
    db_session.commit()

    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/failed-jobs/{job.id}/retry",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "missing required fields" in response.json()["detail"]


def test_agent_run_idempotency(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    message = create_text_message(db_session, data["conversation"].id, "hello again")
    db_session.add(
        AgentRun(
            conversation_id=data["conversation"].id,
            input_message_id=message.id,
            model_name="test",
            prompt_version="v1",
            status=AgentRunStatus.SUCCESS,
        )
    )
    db_session.commit()

    orchestrator = build_orchestrator(
        db_session,
        llm_response={
            "intent": "ask_price",
            "product_reference": {"instagram_post_url": data["post_url"], "instagram_media_id": "media-abc"},
            "slots": {},
            "missing_fields": [],
            "confidence": {"intent": 0.9, "slots": 0.9, "product": 0.9},
            "needs_human": False,
            "human_reason": None,
            "reply_style_hint": None,
        },
    )
    assert orchestrator.process_inbound_message(data["conversation"].id, message.id) is True
    runs = db_session.query(AgentRun).filter(AgentRun.input_message_id == message.id).all()
    assert len(runs) == 1


def test_duplicate_payment_callback_idempotent(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = Order(
        shop_id=demo_shop.id,
        conversation_id=data["conversation"].id,
        customer_id=data["customer"].id,
        status=OrderStatus.PAYMENT_PENDING,
        payment_status=OrderPaymentStatus.PENDING,
        subtotal_amount=Decimal("99.99"),
        total_amount=Decimal("99.99"),
        currency="USD",
        customer_name="Ali Rezaei",
        phone="09121234567",
        city="Tehran",
        address="Valiasr St 10",
        postal_code="1234567890",
    )
    db_session.add(order)
    db_session.commit()

    payment = PaymentService(db_session).initiate_payment(order, provider=PaymentProvider.MOCK)
    service = PaymentService(db_session)
    service.handle_mock_callback(payment.id, PaymentRecordStatus.PAID, provider_reference="sprint-f-ref")
    service.handle_mock_callback(payment.id, PaymentRecordStatus.PAID, provider_reference="sprint-f-ref")
    db_session.refresh(order)
    assert order.payment_status == OrderPaymentStatus.PAID
    assert (
        db_session.query(Order)
        .filter(Order.shop_id == demo_shop.id, Order.payment_status == OrderPaymentStatus.PAID)
        .count()
        == 1
    )
