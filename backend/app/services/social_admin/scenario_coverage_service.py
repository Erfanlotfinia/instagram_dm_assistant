from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.schemas.scenario import ScenarioCoverageRow
from app.services.social_admin.handlers import HANDLER_NAMES

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "scenarios"
    / "social_admin_scenarios.json"
)

PROVIDER_LIST = ["instagram", "whatsapp", "telegram", "bale", "rubika"]

P0_PREFIXES = (
    "ORDER_",
    "PAYMENT_",
    "CANCEL_",
    "CONFIRM_",
    "SPAM_",
    "HUMAN_",
    "SUSPICIOUS_",
    "ABUSE_",
    "LLM_",
)


def _humanize_scenario(code: str) -> str:
    return code.replace("_", " ").lower()


def _priority_for(code: str) -> str:
    upper = code.upper()
    if any(upper.startswith(prefix) or prefix in upper for prefix in P0_PREFIXES):
        return "P0"
    if upper.startswith(("ASK_", "BUY_", "CATALOG_", "PRODUCT_", "BUTTON_")):
        return "P1"
    return "P2"


def _status_for(handler: str, uses_llm: bool) -> str:
    if handler == "LLMFallbackOrchestrator" or uses_llm:
        return "partially_implemented"
    if handler in HANDLER_NAMES or handler.endswith("Handler"):
        return "implemented"
    return "partially_implemented"


class ScenarioCoverageService:
    def load_scenarios(self) -> list[dict[str, Any]]:
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def build_rows(self) -> list[ScenarioCoverageRow]:
        scenarios = self.load_scenarios()
        grouped: dict[str, dict[str, Any]] = {}

        for scenario in scenarios:
            code = scenario["expected_scenario"]
            handler = scenario.get("expected_handler", "")
            uses_llm = bool(scenario.get("expected_uses_llm", False))
            handoff = bool(scenario.get("expected_handoff", False))
            provider = scenario.get("provider", "instagram")

            bucket = grouped.setdefault(
                code,
                {
                    "handlers": set(),
                    "providers": set(),
                    "uses_llm": False,
                    "handoff": False,
                    "test_count": 0,
                },
            )
            bucket["handlers"].add(handler)
            bucket["providers"].add(provider)
            bucket["uses_llm"] = bucket["uses_llm"] or uses_llm
            bucket["handoff"] = bucket["handoff"] or handoff
            bucket["test_count"] += 1

        rows: list[ScenarioCoverageRow] = []
        for code in sorted(grouped):
            meta = grouped[code]
            primary_handler = sorted(meta["handlers"])[0]
            uses_llm = meta["uses_llm"]
            deterministic = not uses_llm and primary_handler != "LLMFallbackOrchestrator"

            rows.append(
                ScenarioCoverageRow(
                    scenario_code=code,
                    scenario_name=_humanize_scenario(code),
                    description=f"Regression pack covers {meta['test_count']} provider variant(s) for {code.replace('_', ' ').lower()}.",
                    supported_providers=sorted(meta["providers"]) or PROVIDER_LIST,
                    current_status=_status_for(primary_handler, uses_llm),
                    deterministic_handler_exists=deterministic,
                    LLM_fallback_exists=uses_llm or "LLMFallback" in primary_handler,
                    human_handoff_exists=meta["handoff"] or re.search(r"handoff|human|complaint|spam", code, re.I) is not None,
                    tests_exist=meta["test_count"] > 0,
                    frontend_support_exists=True,
                    priority=_priority_for(code),
                )
            )
        return rows
