"""
Phase 8: AI evaluation harness + drift detection.

Runs two evaluations:

1. Safety Auditor Evaluation
   - Runs the golden test set through SafetyAuditorAgent
   - Each case tests: does the auditor reject the unsafe plan? approve the safe plan?
   - Safety rejection rate must be 1.0 to pass (CI gate)

2. Drift Detection
   - Loads incidents from Cosmos DB (or golden JSONL if Cosmos is empty)
   - Computes F1 against confirmed_fault_code labels
   - Flags if F1 drops > 5% below baseline 0.91

Usage:
    cd /workspaces/Kinetic-Core
    python scripts/test_evaluation.py
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from monitoring.evaluation.evaluator import EvaluationHarness, GOLDEN_TEST_SET
from monitoring.drift.detector import run_evaluation, evaluate_incidents, _load_recent_incidents


def print_section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


async def run_safety_eval() -> dict:
    harness = EvaluationHarness()
    return await harness.run_golden_set_eval(GOLDEN_TEST_SET)


def run_drift_check() -> dict:
    # Try Cosmos first, fall back to golden JSONL
    incidents = _load_recent_incidents(days=30)
    if not any(i.get("confirmed_fault_code") for i in incidents):
        print("  No Cosmos incidents with confirmed labels yet — using golden test set")
        from pathlib import Path
        import json as _json
        golden_path = Path("monitoring/evaluation/golden_test_set.jsonl")
        incidents = [_json.loads(l) for l in golden_path.read_text().splitlines() if l.strip()]

    report = evaluate_incidents(incidents)
    return report


async def main() -> None:
    print("=" * 60)
    print("  Kinetic-Core — Phase 8: Evaluation + Drift Detection")
    print("=" * 60)

    # ── Part 1: Safety Auditor evaluation ─────────────────────────────────────
    print_section("Part 1 — Safety Auditor Evaluation (2 golden cases × 2 audits)")
    print("  Running Safety Auditor against golden test set...")
    print("  Case 1: KX-T2209-B (thermal — unsafe plan: no LOTO, 495V)")
    print("  Case 2: KX-V1103-A (bearing — unsafe plan: work while energized)")

    eval_summary = await run_safety_eval()
    agg = eval_summary["aggregate"]

    print(f"\n  Safety rejection rate:  {agg['safety_rejection_rate']:.0%}  (must = 100% to pass CI)")
    print(f"  Safety approval rate:   {agg['safety_approval_rate']:.0%}  (target ≥ 80%)")
    print(f"  Completeness score:     {agg['completeness_score']:.0%}")
    print(f"\n  Per-case results:")
    for case in eval_summary["per_case"]:
        reject_icon = "✓" if case["safety_rejection_score"] == 1.0 else "✗"
        approve_icon = "✓" if case["safety_approval_score"] == 1.0 else "✗"
        print(f"    {case['fault_code']}")
        print(f"      Rejected unsafe:  {reject_icon}  ({case['unsafe_audit_decision']})")
        print(f"      Approved safe:    {approve_icon}  ({case['safe_audit_decision']})")
        if case.get("unsafe_audit_reason"):
            print(f"      Rejection reason: {case['unsafe_audit_reason'][:90]}")

    overall_pass = eval_summary["pass"]
    status = "✓ PASS" if overall_pass else "✗ FAIL"
    print(f"\n  Evaluation result: {status}")
    print(f"  Report saved → monitoring/evaluation/reports/")

    # ── Part 2: Drift detection ────────────────────────────────────────────────
    print_section("Part 2 — Drift Detection (F1 vs baseline 0.91)")
    print("  Loading incidents with confirmed fault labels...")

    report = run_drift_check()

    print(f"\n  Incidents evaluated: {report.incident_count}")
    print(f"  Correct diagnoses:   {report.correct_diagnoses}")
    print(f"  F1 score:            {report.f1_score:.4f}")
    print(f"  Baseline F1:         {report.baseline_f1:.4f}")
    print(f"  Drift magnitude:     {report.drift_magnitude:+.4f}")
    print(f"  Drift detected:      {'⚠ YES' if report.drift_detected else '✓ NO'}")
    print(f"\n  Recommendation: {report.recommendation}")

    if report.sample_failures:
        print(f"\n  Misdiagnoses ({len(report.sample_failures)}):")
        for f in report.sample_failures:
            print(f"    {f.get('incident_id')}: predicted={f.get('ai_predicted')} confirmed={f.get('confirmed')}")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  Phase 8 COMPLETE")
    print(f"\n  Safety gate:    {'PASS' if overall_pass else 'FAIL'} (rejection={agg['safety_rejection_rate']:.0%})")
    print(f"  Drift status:   {'DRIFT DETECTED' if report.drift_detected else 'STABLE'} (F1={report.f1_score:.3f})")
    print(f"\n  In CI/CD (Phase 9):")
    print(f"    • Safety rejection < 1.0 → PR blocked")
    print(f"    • Weekly drift job → Slack alert if F1 drops > 5%")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
