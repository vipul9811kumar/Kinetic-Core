"""
/events router — receives telemetry batches from the IoT event processor.
Validates, stores to Cosmos DB, and triggers the agent pipeline if anomaly
flags are present in the batch.
"""

import logging
import os
from datetime import datetime, timezone

from azure.cosmos.aio import CosmosClient
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from api.models.schemas import TelemetryBatch, TelemetryEvent
from agents.orchestrator.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter()

COSMOS_URL = os.environ.get("COSMOS_ENDPOINT", "")
COSMOS_KEY = os.environ.get("COSMOS_KEY", "")
COSMOS_DB = os.environ.get("COSMOS_DB", "kinetic-core")
TELEMETRY_CONTAINER = "telemetry"

_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


async def _store_telemetry(events: list[TelemetryEvent]) -> None:
    if not COSMOS_URL:
        logger.debug("No Cosmos endpoint configured — skipping telemetry storage")
        return
    async with CosmosClient(COSMOS_URL, credential=COSMOS_KEY) as client:
        db = client.get_database_client(COSMOS_DB)
        container = db.get_container_client(TELEMETRY_CONTAINER)
        for event in events:
            doc = event.model_dump(mode="json")
            doc["id"] = f"{event.device_id}_{event.timestamp.isoformat()}"
            doc["_partitionKey"] = event.device_id
            await container.upsert_item(doc)


async def _maybe_trigger_pipeline(
    events: list[TelemetryEvent],
    orchestrator: AgentOrchestrator,
) -> None:
    anomalous = [
        e for e in events
        if (e.fault_flags.thermal_warning or e.fault_flags.flow_deviation
            or e.fault_flags.vibration_alert or e.fault_flags.voltage_anomaly)
    ]
    if not anomalous:
        return

    device_id = anomalous[-1].device_id
    device_window = [e for e in events if e.device_id == device_id]
    window_dicts = [e.model_dump(mode="json") for e in device_window]

    logger.info(f"Anomaly detected on {device_id} — triggering agent pipeline")
    try:
        result = await orchestrator.run_incident(window_dicts)
        logger.info(f"Pipeline complete: incident={result.get('incident_id')}, outcome={result.get('outcome')}")
    except Exception as exc:
        logger.error(f"Agent pipeline failed: {exc}", exc_info=True)


@router.post("/telemetry", status_code=status.HTTP_202_ACCEPTED)
async def ingest_telemetry(
    batch: TelemetryBatch,
    background_tasks: BackgroundTasks,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """
    Accept a batch of telemetry events from the IoT event processor.
    Stores events to Cosmos DB and triggers the agent pipeline in the
    background if any fault flags are raised.
    """
    background_tasks.add_task(_store_telemetry, batch.events)
    background_tasks.add_task(_maybe_trigger_pipeline, batch.events, orchestrator)

    return {
        "accepted": len(batch.events),
        "flagged_events": sum(
            1 for e in batch.events
            if (e.fault_flags.thermal_warning or e.fault_flags.flow_deviation
                or e.fault_flags.vibration_alert or e.fault_flags.voltage_anomaly)
        ),
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
