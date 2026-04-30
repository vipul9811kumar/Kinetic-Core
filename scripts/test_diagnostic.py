"""
Phase 2 smoke test: first real GPT-4o call from DiagnosticLeadAgent.

Generates 60 minutes of thermal_runaway telemetry (1-min intervals),
feeds it to the Diagnostic Lead, and prints the structured result.

Usage:
    cd /workspaces/Kinetic-Core
    python scripts/test_diagnostic.py
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from agents.client import make_openai_client
from agents.diagnostic_lead.agent import DiagnosticLeadAgent
from data.synthetic.telemetry.generator import DEVICE_CONFIGS, generate_stream


async def main() -> None:
    print("=" * 60)
    print("Kinetic-Core — Phase 2: First Real GPT-4o Diagnostic Call")
    print("=" * 60)

    device = DEVICE_CONFIGS[0]
    print(f"\nDevice: {device['device_id']} (Kinetic-Core Model X)")
    print("Scenario: thermal_runaway — Coolant Pump Seal Degradation")
    # Generate 6h at 5-min intervals; take readings from hours 2–5 (the fault development window).
    # Hour 0–2: fault seeding (pre-screener correctly quiet)
    # Hour 2–5: sigmoid degradation is visible — this is what the agent diagnoses
    print("Generating 6 hours of telemetry (5-min intervals), analyzing hours 2–5...\n")

    all_readings = list(generate_stream(device, "thermal_runaway", total_hours=6.0, interval_seconds=300))
    # 5-min intervals → 12 readings/hour; skip first 2 hours (24 readings)
    window = all_readings[24:60]  # hours 2–5 = 36 readings
    print(f"Window: {len(window)} readings")

    first = window[0]["readings"]
    last = window[-1]["readings"]
    print(f"Temp:  {first['temperature_celsius']:.1f}°C → {last['temperature_celsius']:.1f}°C")
    print(f"Flow:  {first['coolant_flow_lpm']:.1f} → {last['coolant_flow_lpm']:.1f} LPM")
    print(f"Vibr:  {first['vibration_mm_s']:.2f} → {last['vibration_mm_s']:.2f} mm/s")

    client = make_openai_client()
    client_type = type(client).__name__
    print(f"\nClient: {client_type}")
    print("Running DiagnosticLeadAgent...\n")

    agent = DiagnosticLeadAgent(client=client)
    result = await agent.analyze(window, incident_id="INC-PHASE2-TEST-001")

    print("-" * 60)
    print(f"Statistical anomalies: {result['statistical_anomalies']}")
    print(f"LLM invoked:          {result['llm_invoked']}")

    if result["llm_invoked"]:
        print(f"\nFault code:     {result['fault_code']}")
        print(f"Description:    {result['fault_description']}")
        print(f"Severity:       {result['severity']}")
        print(f"Confidence:     {result['confidence']:.0%}")
        print(f"Root cause:     {result['root_cause']}")
        print(f"\nReasoning:\n  {result['reasoning']}")
        print(f"\nTokens used:    {result.get('tokens_used', 'n/a')}")
    else:
        print("No anomalies — LLM not invoked (cost $0).")

    print("\n" + "=" * 60)
    print("Full result JSON:")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
