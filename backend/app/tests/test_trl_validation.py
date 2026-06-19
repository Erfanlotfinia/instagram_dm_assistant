from sqlalchemy import select
from sqlalchemy.orm import Session

import pytest

from app.domain.models import AgentAction, Conversation, Customer, InstagramAccount, Message, Order, Product, ProductVariant, TRLValidationScenarioResult
from app.scripts.seed_trl_demo_data import seed_trl_demo_data
from app.services.trl_validation_runner import TRLValidationRunner, THRESHOLDS


def test_seed_trl_demo_data_works(db_session: Session):
    summary = seed_trl_demo_data(reset=True, db=db_session)
    assert summary["products"] >= 20
    assert db_session.scalar(select(Product).where(Product.shop_id == summary["shop_id"]).limit(1)) is not None
    assert db_session.query(ProductVariant).join(Product).filter(Product.shop_id == summary["shop_id"]).count() >= 100


def test_trl_runner_runs_scenarios_and_stores_results(db_session: Session):
    summary = seed_trl_demo_data(reset=True, db=db_session)
    runner = TRLValidationRunner(db_session)
    run = runner.run(summary["shop_id"], scenario_limit=5)
    assert run.status == "completed"
    assert run.total_scenarios == 5
    assert db_session.query(TRLValidationScenarioResult).filter_by(run_id=run.id).count() == 5
    assert "intent_accuracy" in run.metrics_json
    assert "thresholds_passed" in run.metrics_json


def test_trl_simulation_does_not_send_real_messages(db_session: Session):
    summary = seed_trl_demo_data(reset=True, db=db_session)
    run = TRLValidationRunner(db_session).run(summary["shop_id"], scenario_limit=3)
    assert db_session.query(Message).filter(Message.is_simulation.is_(False), Message.instagram_message_id.like(f"trl:{run.id}%")).count() == 0
    assert db_session.query(AgentAction).filter(AgentAction.action_name == "send_outbound").count() == 0


def test_trl_failed_scenarios_include_reasons_and_thresholds(db_session: Session):
    summary = seed_trl_demo_data(reset=True, db=db_session)
    run = TRLValidationRunner(db_session).run(summary["shop_id"], scenario_limit=8)
    failed = db_session.query(TRLValidationScenarioResult).filter_by(run_id=run.id, passed=False).first()
    if failed is not None:
        assert failed.failure_reasons
    assert set(THRESHOLDS).issubset(run.metrics_json["thresholds"])


def test_trl_shop_isolation(db_session: Session, demo_shop):
    summary = seed_trl_demo_data(reset=True, db=db_session)
    runner = TRLValidationRunner(db_session)
    run = runner.run(summary["shop_id"], scenario_limit=2)
    assert runner.get_run(demo_shop.id, run.id) is None
    assert runner.list_results(demo_shop.id, run.id) == []


def test_trl_runner_can_run_twice_without_customer_unique_collision(db_session: Session):
    summary = seed_trl_demo_data(reset=True, db=db_session)
    runner = TRLValidationRunner(db_session)
    first = runner.run(summary["shop_id"], scenario_limit=1)
    second = runner.run(summary["shop_id"], scenario_limit=1)
    assert first.status == "completed"
    assert second.status == "completed"


def test_trl_deterministic_mode_labels_metrics(db_session: Session):
    summary = seed_trl_demo_data(reset=True, db=db_session)
    run = TRLValidationRunner(db_session).run(
        summary["shop_id"],
        scenario_limit=2,
        validation_mode="deterministic_regression",
    )
    assert run.validation_mode == "deterministic_regression"
    assert run.metrics_json["validation_mode"] == "deterministic_regression"
    assert run.metrics_json["proves_live_llm"] is False
    assert run.metrics_json["model_version"] == "trl-rule-based-simulator"


def test_trl_live_llm_mode_requires_enabled_flag(db_session: Session, monkeypatch) -> None:
    monkeypatch.setenv("TRL_LIVE_LLM_ENABLED", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    summary = seed_trl_demo_data(reset=True, db=db_session)
    with pytest.raises(ValueError, match="TRL live LLM staging requires"):
        TRLValidationRunner(db_session).run(
            summary["shop_id"],
            scenario_limit=1,
            validation_mode="live_llm_staging",
        )
    get_settings.cache_clear()


def test_trl_reset_only_deletes_trl_owned_simulation_records(db_session: Session):
    summary = seed_trl_demo_data(reset=True, db=db_session)
    shop_id = summary["shop_id"]
    runner = TRLValidationRunner(db_session)
    run = runner.run(shop_id, scenario_limit=1)

    ig = db_session.scalar(select(InstagramAccount).where(InstagramAccount.shop_id == shop_id).limit(1))
    from app.services.legacy_channel_compat import ensure_channel_account_for_legacy_instagram

    channel_account = ensure_channel_account_for_legacy_instagram(db_session, ig)
    customer = Customer(shop_id=shop_id, instagram_user_id="simulator_customer", full_name="Simulator Customer")
    db_session.add(customer); db_session.flush()
    simulator_conversation = Conversation(
        shop_id=shop_id,
        instagram_account_id=ig.id,
        channel_account_id=channel_account.id,
        customer_id=customer.id,
        channel_provider="instagram",
        external_conversation_id="simulator:unrelated",
        channel_conversation_id="simulator:unrelated",
        channel_customer_id=customer.instagram_user_id,
        is_simulation=True,
    )
    db_session.add(simulator_conversation); db_session.flush()
    simulator_order = Order(
        shop_id=shop_id,
        customer_id=customer.id,
        conversation_id=simulator_conversation.id,
        customer_name="Simulator Customer",
        phone="09120000000",
        city="Tehran",
        address="Simulator Street",
        postal_code="12345",
        is_simulation=True,
    )
    db_session.add(simulator_order); db_session.commit()

    summary = runner.reset(shop_id)

    assert summary["deleted_runs"] >= 1
    assert db_session.get(Conversation, simulator_conversation.id) is not None
    assert db_session.get(Order, simulator_order.id) is not None
    assert (
        db_session.query(Conversation)
        .filter(Conversation.channel_conversation_id.like(f"trl:{run.id}:%"))
        .count()
        == 0
    )
