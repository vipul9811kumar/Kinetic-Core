"""
Phase 5: Full 4-agent pipeline end-to-end with real Azure resources.

Pipeline:
  synthetic telemetry (thermal_runaway)
  → DiagnosticLead  (GPT-4o statistical + LLM diagnosis)
  → TechnicalLibrarian  (hybrid RAG → AI Search → GPT-4o synthesis)
  → SafetyAuditor  (hard rules + GPT-4o adversarial gate)
  → Work Order  (if approved)
  → Cosmos DB  (incident + work order persisted)

Usage:
    cd /workspaces/Kinetic-Core
    python scripts/test_full_pipeline.py
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from agents.orchestrator.orchestrator import AgentOrchestrator
from data.synthetic.telemetry.generator import DEVICE_CONFIGS, generate_stream


def print_section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


async def main() -> None:
    print("=" * 60)
    print("  Kinetic-Core — Phase 5: Full Pipeline End-to-End")
    print("=" * 60)

    device = DEVICE_CONFIGS[0]
    print(f"\nDevice:   {device['device_id']}")
    print(f"Scenario: vibration_bearing (KX-V1103-A — Pump Bearing Micro-Failure)")
    print(f"Window:   hours 1–3 — strong vibration trend, temp ~42°C (safe to work on)")

    # vibration_bearing: rising vibration catches the bearing fault while the machine
    # is still at safe temperature (42°C) and voltage (478V < 480V limit).
    # Safety Auditor should issue GO — producing a real dispatched work order.
    all_readings = list(generate_stream(device, "vibration_bearing", total_hours=5.0, interval_seconds=300))
    # Dynamically find the best 20-reading window where:
    #   voltage < 480V (hard rule won't block), vibration trend detectable, temp safe
    window = None
    for end in range(20, len(all_readings)):
        w = all_readings[end - 20:end]
        last = w[-1]["readings"]
        if last["voltage_v"] >= 480.0:
            continue
        vibrs = [r["readings"]["vibration_mm_s"] for r in w]
        trend = (vibrs[-1] - vibrs[0]) / len(vibrs)
        if trend >= 0.04:
            window = w
            break
    if window is None:
        raise RuntimeError("Could not find a valid window — re-run to get different noise values")

    first = window[0]["readings"]
    last = window[-1]["readings"]
    print(f"\nTelemetry: temp {first['temperature_celsius']:.1f}→{last['temperature_celsius']:.1f}°C  "
          f"flow {first['coolant_flow_lpm']:.0f}→{last['coolant_flow_lpm']:.0f} LPM  "
          f"vibr {first['vibration_mm_s']:.2f}→{last['vibration_mm_s']:.2f} mm/s  "
          f"volt {last['voltage_v']:.1f}V")

    orchestrator = AgentOrchestrator()

    print("\nRunning pipeline (this will make ~4-5 GPT-4o calls)...")
    result = await orchestrator.run_incident(window)
    await orchestrator.close()

    # ── Stage 1: Diagnostic ────────────────────────────────────────────────────
    print_section("Stage 1 — Diagnostic Lead")
    diag = result["stages"].get("diagnostic", {})
    print(f"  Fault code:   {diag.get('fault_code')}")
    print(f"  Severity:     {diag.get('severity')}")
    print(f"  Confidence:   {diag.get('confidence', 0):.0%}")
    print(f"  Anomalies:    {diag.get('statistical_anomalies')}")
    print(f"  Root cause:   {diag.get('root_cause')}")
    print(f"  LLM tokens:   {diag.get('tokens_used', 'n/a')}")

    # ── Stage 2: Librarian ─────────────────────────────────────────────────────
    lib = result["stages"].get("librarian", {})
    if lib:
        print_section("Stage 2 — Technical Librarian (Hybrid RAG)")
        print(f"  Chunks retrieved: {lib.get('retrieval_count')}")
        print(f"  Faithfulness:     {lib.get('faithfulness_score', 0):.0%}")
        print(f"  Flagged review:   {lib.get('requires_human_review')}")
        print(f"  Est. duration:    {lib.get('estimated_duration_minutes')} min")
        print(f"  Team size:        {lib.get('team_size')}")
        print(f"  Safety prereqs:   {lib.get('safety_prerequisites')}")
        print(f"\n  Repair steps ({len(lib.get('repair_steps', []))}):")
        for step in lib.get("repair_steps", [])[:5]:
            crit = " ⚠" if step.get("safety_critical") else ""
            print(f"    {step['step']}. {step['action'][:80]}{crit}")
        if len(lib.get("repair_steps", [])) > 5:
            print(f"    ... +{len(lib['repair_steps']) - 5} more steps")

    # ── Stage 3: Safety Auditor ────────────────────────────────────────────────
    audit = result["stages"].get("safety_audit", {})
    if audit:
        print_section("Stage 3 — Safety Auditor")
        decision = audit.get("decision", "UNKNOWN")
        icon = "✓ GO" if decision == "GO" else ("⚠ GO_WITH_CONDITIONS" if "CONDITIONS" in decision else "✗ NO_GO")
        print(f"  Decision:       {icon}")
        print(f"  Reason:         {audit.get('reason', '')[:120]}")
        print(f"  Arc flash:      {audit.get('arc_flash_rating')}")
        print(f"  PPE required:   {audit.get('ppe_required', 'n/a')}")
        print(f"  Hard rule hit:  {audit.get('hard_rule_triggered')}")
        if audit.get("conditions"):
            print(f"  Conditions:     {audit['conditions']}")

    # ── Stage 4: Work Order ────────────────────────────────────────────────────
    wo = result["stages"].get("work_order", {})
    if wo:
        print_section("Stage 4 — Work Order")
        print(f"  Work Order ID:  {wo.get('work_order_id')}")
        print(f"  Priority:       {wo.get('priority')}")
        print(f"  Status:         {wo.get('status')}")
        print(f"  Parts required: {[p['part_name'] for p in wo.get('parts_required', [])]}")

    # ── Outcome ────────────────────────────────────────────────────────────────
    print_section("Pipeline Outcome")
    print(f"  Incident ID:  {result['incident_id']}")
    print(f"  Outcome:      {result.get('outcome')}")
    print(f"  Work Order:   {result.get('work_order_id', 'n/a')}")
    print(f"  Persisted:    Cosmos DB incidents + work-orders containers")

    print("\n" + "=" * 60)
    print("  Phase 5 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
