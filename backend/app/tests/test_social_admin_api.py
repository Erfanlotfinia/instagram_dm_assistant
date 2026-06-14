from app.services.social_admin.scenario_coverage_service import ScenarioCoverageService
from app.tests.fixtures.agent import seed_order_flow_data


def test_scenario_coverage_rows_from_fixture():
    rows = ScenarioCoverageService().build_rows()
    assert len(rows) >= 20
    assert all(row.tests_exist for row in rows)
    assert any(row.scenario_code == "ASK_PRICE_REFERENCED_PRODUCT" for row in rows)


def test_admin_task_create_and_approve(client, auth_headers, demo_shop):
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/admin-tasks",
        headers=auth_headers,
        json={"task_type": "draft_post_caption", "context": "Summer sandals launch"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["requires_approval"] is True
    assert body["output_json"]["auto_publish"] is False
    assert "Summer sandals launch" in body["output_json"]["draft"]

    approve = client.post(
        f"/api/v1/shops/{demo_shop.id}/admin-tasks/{body['id']}/approve",
        headers=auth_headers,
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"


def test_operator_correction_creates_suggestion(client, auth_headers, demo_shop, db_session):
    seeded = seed_order_flow_data(db_session, demo_shop)
    conversation_id = str(seeded["conversation"].id)

    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/operator-corrections",
        headers=auth_headers,
        json={
            "conversation_id": conversation_id,
            "before_json": {"scenario": "ASK_PRICE_REFERENCED_PRODUCT", "response": "Wrong price"},
            "after_json": {
                "scenario": "ASK_STOCK_REFERENCED_PRODUCT",
                "response": "This item is in stock.",
            },
        },
    )
    assert response.status_code == 201
    corrections = response.json()
    assert len(corrections) == 2

    suggestions = client.get(
        f"/api/v1/shops/{demo_shop.id}/automation-suggestions",
        headers=auth_headers,
    )
    assert suggestions.status_code == 200
    items = suggestions.json()
    assert len(items) >= 2
    assert items[0]["status"] == "pending"

    approved = client.post(
        f"/api/v1/shops/{demo_shop.id}/automation-suggestions/{items[0]['id']}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_automation_rules_endpoint(client, auth_headers, demo_shop):
    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/automation-rules",
        headers=auth_headers,
    )
    assert response.status_code == 200
    steps = response.json()
    assert len(steps) == 8
    assert steps[0]["tier"] == "deterministic"
    assert steps[-1]["tier"] == "human"
