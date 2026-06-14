"""Run social admin scenario regression suite and print metrics."""

from __future__ import annotations

import json
import sys

from app.db.session import SessionLocal
from app.services.social_admin.scenario_regression_runner import ScenarioRegressionRunner


def main() -> int:
    with SessionLocal() as db:
        metrics = ScenarioRegressionRunner(db).run()
    print(json.dumps(metrics.model_dump(), indent=2))
    if metrics.unsafe_action_count or metrics.false_order_count or metrics.false_payment_count:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
