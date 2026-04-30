"""
Azure Function: IoT Hub Event Processor

Triggered by the IoT Hub Event Hub-compatible endpoint (EventHub trigger).
Each invocation receives a batch of device messages, validates them,
enriches with fault flags, stores to Cosmos DB, and triggers the
agent pipeline when anomalies are present.

Deploy:
    func azure functionapp publish kcore-func-dev

Local test:
    python scripts/test_event_processor.py
"""

import json
import logging
import os
from datetime import datetime, timezone

import azure.functions as func

logger = logging.getLogger(__name__)

COSMOS_URL = os.environ.get("COSMOS_ENDPOINT", "")
COSMOS_KEY = os.environ.get("COSMOS_KEY", "")
COSMOS_DB = os.environ.get("COSMOS_DB", "kinetic-core")
API_BASE_URL = os.environ.get("KINETIC_CORE_API_URL", "http://localhost:8000")

# Fault detection thresholds (mirrors statistical_screen in DiagnosticLeadAgent)
THRESHOLDS = {
    "thermal_warning": 75.0,       # °C
    "flow_deviation_lpm": 150.0,   # LPM minimum
    "vibration_alert": 4.5,        # mm/s
    "voltage_low": 440.0,          # V
    "voltage_high": 510.0,         # V
}

app = func.FunctionApp()


def _validate_payload(payload: dict) -> bool:
    return {"device_id", "timestamp", "readings"}.issubset(payload.keys())


def _enrich_payload(payload: dict) -> dict:
    payload["ingested_at"] = datetime.now(timezone.utc).isoformat()
    payload["schema_version"] = "1.0"
    r = payload.get("readings", {})

    # Compute fault flags if not already present from the device
    if not payload.get("fault_flags"):
        payload["fault_flags"] = {
            "thermal_warning": r.get("temperature_celsius", 0) > THRESHOLDS["thermal_warning"],
            "flow_deviation":  r.get("coolant_flow_lpm", 185) < THRESHOLDS["flow_deviation_lpm"],
            "vibration_alert": r.get("vibration_mm_s", 0) > THRESHOLDS["vibration_alert"],
            "voltage_anomaly": (
                r.get("voltage_v", 480) < THRESHOLDS["voltage_low"] or
                r.get("voltage_v", 480) > THRESHOLDS["voltage_high"]
            ),
        }
    return payload


@app.event_hub_message_trigger(
    arg_name="events",
    event_hub_name="messages/events",
    connection="IOTHUB_EVENT_HUB_CONNECTION_STRING",
    cardinality="many",
    consumer_group="$Default",
)
async def process_iothub_messages(events: list[func.EventHubEvent]) -> None:
    """Batch handler — processes all messages in the EventHub checkpoint window."""
    logger.info(f"EventHub trigger: received batch of {len(events)} messages")

    for event in events:
        try:
            body = json.loads(event.get_body().decode("utf-8"))
        except Exception as exc:
            logger.error(f"Failed to parse EventHub message: {exc}")
            continue

        if not _validate_payload(body):
            logger.warning(f"Invalid payload — skipping: {list(body.keys())}")
            continue

        enriched = _enrich_payload(body)
        await _store_to_cosmos(enriched)

        if any(enriched["fault_flags"].values()):
            logger.info(f"Fault flags active for {enriched['device_id']} — triggering pipeline")
            await _forward_to_api([enriched])


async def _store_to_cosmos(payload: dict) -> None:
    if not COSMOS_URL:
        return
    from azure.cosmos.aio import CosmosClient
    async with CosmosClient(COSMOS_URL, credential=COSMOS_KEY) as client:
        container = client.get_database_client(COSMOS_DB).get_container_client("telemetry")
        doc = {
            "id": f"{payload['device_id']}_{payload['timestamp']}",
            "device_id": payload["device_id"],
            **payload,
        }
        await container.upsert_item(doc)
        logger.debug(f"Stored: {doc['id']}")


async def _forward_to_api(events: list[dict]) -> None:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{API_BASE_URL}/events/telemetry", json={"events": events})
            resp.raise_for_status()
            logger.info(f"API accepted {len(events)} events: HTTP {resp.status_code}")
    except Exception as exc:
        logger.error(f"API forward failed: {exc}", exc_info=True)
