from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import AgentAction, Message, Product, ProductVariant, TRLValidationScenarioResult
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
