"""Generate a markdown summary of the latest TRL validation run and pilot readiness.

Usage:
    python -m app.scripts.generate_trl_report
    python -m app.scripts.generate_trl_report --shop-slug trl-commerce-demo
    python -m app.scripts.generate_trl_report --output /tmp/trl_report.md
"""
from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.domain.models import Shop, TRLValidationRun
from app.services.pilot_service import PilotService
from app.services.trl_validation_runner import THRESHOLDS, TRLValidationRunner


def _fmt_pct(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value * 100:.1f}%"
    return "—"


def _fmt_bool(value: Any) -> str:
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    return "MISSING"


def _threshold_table(metrics: dict[str, Any]) -> list[str]:
    passed = metrics.get("thresholds_passed") or {}
    lines = ["| Metric | Result | Threshold | Status |", "|--------|--------|-----------|--------|"]
    for key, threshold in THRESHOLDS.items():
        result = metrics.get(key, "MISSING")
        if isinstance(result, float) and (key.endswith("_accuracy") or key.endswith("_rate")):
            result_str = _fmt_pct(result)
        else:
            result_str = str(result)
        if isinstance(threshold, float):
            threshold_str = f"≥ {_fmt_pct(threshold)}" if "accuracy" in key or "rate" in key else str(threshold)
        else:
            threshold_str = f"≤ {threshold}"
        status = _fmt_bool(passed.get(key))
        lines.append(f"| {key} | {result_str} | {threshold_str} | {status} |")
    return lines


def build_report(*, shop_slug: str | None = None) -> str:
    with SessionLocal() as db:
        if shop_slug:
            shop = db.scalar(select(Shop).where(Shop.slug == shop_slug))
            if shop is None:
                raise SystemExit(f"Shop not found for slug: {shop_slug}")
        else:
            shop = db.scalar(
                select(Shop).where(Shop.slug == "trl-commerce-demo").limit(1)
            ) or db.scalar(select(Shop).order_by(Shop.created_at.asc()).limit(1))
            if shop is None:
                raise SystemExit("No shops found in database.")

        latest = db.scalar(
            select(TRLValidationRun)
            .where(TRLValidationRun.shop_id == shop.id)
            .order_by(TRLValidationRun.started_at.desc())
            .limit(1)
        )
        readiness = PilotService(db).readiness(shop.id)
        generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        lines = [
            "# TRL Report Summary",
            "",
            f"**Generated:** {generated_at}  ",
            f"**Shop:** {shop.name} (`{shop.slug}`)  ",
            f"**Shop ID:** `{shop.id}`  ",
            "",
            "---",
            "",
            "## Latest TRL validation run",
            "",
        ]

        if latest is None:
            lines.extend([
                "**Status:** MISSING — no TRL validation runs found for this shop.",
                "",
                "Run validation:",
                "```bash",
                f"curl -X POST -H \"Authorization: Bearer <token>\" \\",
                f"  -d '{{\"reset_demo_data\": true}}' \\",
                f"  {get_settings().public_api_base_url.rstrip('/')}/api/v1/shops/{shop.id}/trl-validation/run",
                "```",
                "",
            ])
        else:
            metrics = latest.metrics_json or {}
            thresholds_passed = metrics.get("thresholds_passed") or {}
            all_passed = bool(thresholds_passed) and all(bool(v) for v in thresholds_passed.values())
            pass_rate = (
                latest.passed_scenarios / latest.total_scenarios
                if latest.total_scenarios
                else 0
            )

            lines.extend([
                f"| Field | Value |",
                f"|-------|-------|",
                f"| Run ID | `{latest.id}` |",
                f"| Status | `{latest.status}` |",
                f"| Started | {latest.started_at.isoformat()} |",
                f"| Completed | {latest.completed_at.isoformat() if latest.completed_at else '—'} |",
                f"| Scenarios | {latest.passed_scenarios}/{latest.total_scenarios} passed ({_fmt_pct(pass_rate)}) |",
                f"| All thresholds passed | {'yes' if all_passed else 'no' if thresholds_passed else 'MISSING'} |",
                "",
                "### Threshold comparison",
                "",
                *_threshold_table(metrics),
                "",
                "### Key metrics",
                "",
                f"- Average processing time: {metrics.get('average_processing_time_ms', 'MISSING')} ms",
                f"- P95 processing time: {metrics.get('p95_processing_latency', 'MISSING')} ms",
                f"- Failed scenario count: {metrics.get('failed_scenario_count', 'MISSING')}",
                f"- Handoff precision: {_fmt_pct(metrics.get('handoff_precision'))}",
                f"- Handoff recall: {_fmt_pct(metrics.get('handoff_recall'))}",
                "",
            ])

            failed = TRLValidationRunner(db).list_results(shop.id, latest.id, passed=False)
            lines.append("### Failed scenarios")
            lines.append("")
            if not failed:
                lines.append("No failed scenarios.")
            else:
                lines.append("| Scenario | Reasons |")
                lines.append("|----------|---------|")
                for row in failed[:20]:
                    reasons = "; ".join(row.failure_reasons) if row.failure_reasons else "—"
                    lines.append(f"| {row.scenario_id} | {reasons} |")
                if len(failed) > 20:
                    lines.append(f"| … | {len(failed) - 20} more |")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## Pilot readiness",
            "",
            f"**ready_for_trl6_pilot:** `{readiness.ready_for_trl6_pilot}`",
            "",
            "### Criteria",
            "",
            "| Criterion | Passed | Detail |",
            "|-----------|:------:|--------|",
        ])
        for item in readiness.criteria:
            detail = f" — {item.detail}" if item.detail else ""
            lines.append(f"| {item.label} | {'✅' if item.passed else '❌'} |{detail} |")

        lines.extend([
            "",
            "### Checklist",
            "",
            "| Item | Passed | Detail |",
            "|------|:------:|--------|",
        ])
        for item in readiness.checklist:
            detail = f" — {item.detail}" if item.detail else ""
            lines.append(f"| {item.label} | {'✅' if item.passed else '❌'} |{detail} |")

        if readiness.warnings:
            lines.extend(["", "### Warnings", ""])
            for warning in readiness.warnings:
                lines.append(f"- {warning}")

        lines.extend([
            "",
            "---",
            "",
            "## TRL assessment (automated summary)",
            "",
        ])

        if latest is None:
            lines.append("**TRL 5:** Cannot assess — no validation run.")
        else:
            metrics = latest.metrics_json or {}
            thresholds_passed = metrics.get("thresholds_passed") or {}
            all_passed = bool(thresholds_passed) and all(bool(v) for v in thresholds_passed.values())
            lines.append(f"**TRL 5 threshold gate:** {'PASS' if all_passed else 'FAIL or INCOMPLETE'}")
            lines.append("")
            lines.append(
                "Note: TRL runner uses rule-based LLM substitute by default; "
                "stubbed metrics (security, idempotency, payment, inventory) may show PASS without independent verification."
            )

        lines.append("")
        lines.append(
            f"**TRL 6 pilot-ready (API):** {'YES' if readiness.ready_for_trl6_pilot else 'NO'}"
        )
        lines.append("")
        return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate TRL validation and pilot readiness markdown report.")
    parser.add_argument("--shop-slug", default=None, help="Shop slug (default: trl-commerce-demo or first shop)")
    parser.add_argument("--output", "-o", default=None, help="Write report to file instead of stdout")
    args = parser.parse_args(argv)

    report = build_report(shop_slug=args.shop_slug)
    if args.output:
        path = Path(args.output)
        path.write_text(report, encoding="utf-8")
        print(f"Wrote report to {path}", file=sys.stderr)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
