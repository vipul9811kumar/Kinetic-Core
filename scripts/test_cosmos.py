"""
Phase 3 smoke test: persist a diagnostic result to Cosmos DB and read it back.

Usage:
    cd /workspaces/Kinetic-Core
    python scripts/test_cosmos.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from agents.client import make_openai_client
from agents.cosmos_store import CosmosStore
from agents.diagnostic_lead.agent import DiagnosticLeadAgent
from azure.cosmos.aio import CosmosClient
from data.synthetic.telemetry.generator import DEVICE_CONFIGS, generate_stream


async def main() -> None:
    print("=" * 60)
    print("Kinetic-Core — Phase 3: Cosmos DB Persistence Test")
    print("=" * 60)

    # Generate fault window (hours 2–5 of thermal runaway)
    device = DEVICE_CONFIGS[0]
    all_readings = list(generate_stream(device, "thermal_runaway", total_hours=6.0, interval_seconds=300))
    window = all_readings[24:60]
    print(f"\nTelemetry window: {len(window)} readings (hours 2–5 thermal runaway)")

    # Run diagnostic agent
    print("Running DiagnosticLeadAgent...")
    client = make_openai_client()
    agent = DiagnosticLeadAgent(client=client)
    result = await agent.analyze(window, incident_id="INC-PHASE3-TEST-001")
    print(f"  Fault code: {result['fault_code']}  Severity: {result['severity']}  Confidence: {result['confidence']:.0%}")

    # Wrap in a minimal incident trace (normally built by orchestrator)
    trace = {
        "incident_id": "INC-PHASE3-TEST-001",
        "device_id": device["device_id"],
        "started_at": result["analyzed_at"],
        "resolved_at": result["analyzed_at"],
        "outcome": "DIAGNOSTIC_ONLY",
        "stages": {"diagnostic": result},
    }

    # Persist to Cosmos
    print("\nPersisting to Cosmos DB incidents container...")
    store = CosmosStore()
    await store.save_incident(trace)
    print("  Written OK")

    # Read back to verify
    print("Reading back from Cosmos DB...")
    cosmos_client = CosmosClient(
        url=os.environ["COSMOS_ENDPOINT"],
        credential=os.environ["COSMOS_KEY"],
    )
    db = cosmos_client.get_database_client(os.environ.get("COSMOS_DB", "kinetic-core"))
    container = db.get_container_client("incidents")
    doc = await container.read_item(item="INC-PHASE3-TEST-001", partition_key=device["device_id"])

    print(f"\n  id:         {doc['id']}")
    print(f"  device_id:  {doc['device_id']}")
    print(f"  outcome:    {doc['outcome']}")
    print(f"  fault_code: {doc['stages']['diagnostic']['fault_code']}")
    print(f"  saved_at:   {doc['saved_at']}")

    await cosmos_client.close()
    await store.close()

    print("\n" + "=" * 60)
    print("Phase 3 COMPLETE — incident persisted and read back from Cosmos DB")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
