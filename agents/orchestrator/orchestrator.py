"""
Kinetic-Core Orchestrator Agent

Coordinates the multi-agent pipeline:
  Diagnostic Lead → Technical Librarian → Safety Auditor → Work Order

Each agent's reasoning trace is persisted to Cosmos DB under the incident_id
so the full lifecycle can be replayed for audit or retraining.
"""

import argparse
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from agents.client import make_openai_client
from agents.cosmos_store import CosmosStore
from agents.diagnostic_lead.agent import DiagnosticLeadAgent
from agents.technical_librarian.agent import TechnicalLibrarianAgent
from agents.safety_auditor.agent import SafetyAuditorAgent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class AgentOrchestrator:
    def __init__(self):
        self.client = make_openai_client()
        self.diagnostic_lead = DiagnosticLeadAgent(self.client)
        self.technical_librarian = TechnicalLibrarianAgent(self.client)
        self.safety_auditor = SafetyAuditorAgent(self.client)
        self.store = CosmosStore()

    async def run_incident(self, telemetry_window: list[dict]) -> dict:
        incident_id = f"INC-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"
        started_at = datetime.now(timezone.utc)

        logger.info(f"[{incident_id}] Orchestrator: starting incident pipeline")

        trace = {
            "incident_id": incident_id,
            "started_at": started_at.isoformat(),
            "device_id": telemetry_window[-1]["device_id"],
            "telemetry_window_size": len(telemetry_window),
            "stages": {},
        }

        # Stage 1: Diagnostic Lead
        logger.info(f"[{incident_id}] Stage 1: Diagnostic Lead analyzing {len(telemetry_window)} readings")
        diagnostic_result = await self.diagnostic_lead.analyze(
            telemetry_window=telemetry_window,
            incident_id=incident_id,
        )
        trace["stages"]["diagnostic"] = diagnostic_result

        if diagnostic_result["severity"] == "LOW" and not diagnostic_result["fault_code"]:
            logger.info(f"[{incident_id}] Diagnostic: no actionable fault detected. Closing incident.")
            trace["outcome"] = "NO_FAULT"
            trace["resolved_at"] = datetime.now(timezone.utc).isoformat()
            await self.store.save_incident(trace)
            return trace

        logger.info(
            f"[{incident_id}] Diagnostic: fault_code={diagnostic_result['fault_code']}, "
            f"severity={diagnostic_result['severity']}"
        )

        # Stage 2: Technical Librarian
        logger.info(f"[{incident_id}] Stage 2: Technical Librarian looking up {diagnostic_result['fault_code']}")
        librarian_result = await self.technical_librarian.lookup(
            fault_code=diagnostic_result["fault_code"],
            root_cause=diagnostic_result["root_cause"],
            incident_id=incident_id,
        )
        trace["stages"]["librarian"] = librarian_result

        logger.info(
            f"[{incident_id}] Librarian: found {len(librarian_result['repair_steps'])} repair steps, "
            f"faithfulness={librarian_result['faithfulness_score']:.2f}"
        )

        # Stage 3: Safety Auditor
        latest_reading = telemetry_window[-1]["readings"]
        logger.info(f"[{incident_id}] Stage 3: Safety Auditor validating repair plan")
        audit_result = await self.safety_auditor.validate(
            repair_plan=librarian_result,
            live_readings=latest_reading,
            incident_id=incident_id,
        )
        trace["stages"]["safety_audit"] = audit_result

        logger.info(
            f"[{incident_id}] Safety Audit: decision={audit_result['decision']}, "
            f"reason={audit_result['reason'][:80]}"
        )

        if audit_result["decision"] == "NO_GO":
            trace["outcome"] = "BLOCKED_BY_SAFETY"
            trace["safety_block_reason"] = audit_result["reason"]
            trace["resolved_at"] = datetime.now(timezone.utc).isoformat()
            logger.warning(f"[{incident_id}] Work order BLOCKED by Safety Auditor: {audit_result['reason']}")
            await self.store.save_incident(trace)
            return trace

        # Stage 4: Generate Work Order
        work_order = self._generate_work_order(incident_id, diagnostic_result, librarian_result, audit_result)
        trace["stages"]["work_order"] = work_order
        trace["outcome"] = "WORK_ORDER_DISPATCHED"
        trace["work_order_id"] = work_order["work_order_id"]
        trace["resolved_at"] = datetime.now(timezone.utc).isoformat()

        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        logger.info(
            f"[{incident_id}] Pipeline complete in {elapsed:.1f}s. "
            f"Work order {work_order['work_order_id']} dispatched."
        )

        await self.store.save_incident(trace)
        await self.store.save_work_order(work_order)
        return trace

    async def close(self) -> None:
        await self.store.close()

    def _generate_work_order(
        self,
        incident_id: str,
        diagnostic: dict,
        librarian: dict,
        audit: dict,
    ) -> dict:
        wo_id = f"WO-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        return {
            "work_order_id": wo_id,
            "incident_id": incident_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "priority": diagnostic["severity"],
            "fault_code": diagnostic["fault_code"],
            "fault_description": diagnostic["fault_description"],
            "device_id": diagnostic.get("device_id"),
            "repair_steps": librarian["repair_steps"],
            "parts_required": librarian["parts_list"],
            "estimated_duration_minutes": librarian["estimated_duration_minutes"],
            "safety_clearance": {
                "approved_by": "Safety Auditor v1.0",
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "voltage_at_approval": audit.get("voltage_checked"),
                "arc_flash_rating": audit.get("arc_flash_rating"),
            },
            "status": "DISPATCHED",
            "source_citations": librarian.get("source_citations", []),
        }


async def run_demo(scenario: str = "thermal_runaway"):
    """Run a demo incident using synthetic telemetry."""
    import sys
    sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
    from data.synthetic.telemetry.generator import generate_stream, DEVICE_CONFIGS, FAULT_SCENARIOS

    device = DEVICE_CONFIGS[0]
    readings = list(generate_stream(device, scenario, total_hours=4.0, interval_seconds=300))
    logger.info(f"Loaded {len(readings)} synthetic telemetry points for scenario: {scenario}")

    orchestrator = AgentOrchestrator()
    result = await orchestrator.run_incident(readings)

    print("\n" + "=" * 60)
    print("KINETIC-CORE INCIDENT LIFECYCLE COMPLETE")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="Kinetic-Core Orchestrator")
    parser.add_argument("--scenario", default="thermal_runaway", help="Fault scenario to simulate")
    parser.add_argument("--demo", action="store_true", help="Run with synthetic data (no Azure required)")
    args = parser.parse_args()

    asyncio.run(run_demo(args.scenario))


if __name__ == "__main__":
    main()
