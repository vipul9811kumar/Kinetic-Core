"""
Cosmos DB persistence for agent traces and work orders.

Provides a thin async wrapper around the Azure Cosmos SDK.
Each write uses upsert so reprocessed incidents don't create duplicates.
"""

import os
from datetime import datetime, timezone

from azure.cosmos.aio import CosmosClient


class CosmosStore:
    def __init__(self):
        endpoint = os.environ["COSMOS_ENDPOINT"]
        key = os.environ["COSMOS_KEY"]
        db_name = os.environ.get("COSMOS_DB", "kinetic-core")

        self._client = CosmosClient(url=endpoint, credential=key)
        self._db_name = db_name

    async def _container(self, name: str):
        db = self._client.get_database_client(self._db_name)
        return db.get_container_client(name)

    async def save_incident(self, trace: dict) -> None:
        """Persist the full orchestrator trace to the incidents container."""
        container = await self._container("incidents")
        doc = {
            "id": trace["incident_id"],
            "device_id": trace["device_id"],
            "saved_at": datetime.now(timezone.utc).isoformat(),
            **trace,
        }
        await container.upsert_item(doc)

    async def save_work_order(self, work_order: dict) -> None:
        """Persist a dispatched work order."""
        container = await self._container("work-orders")
        doc = {
            "id": work_order["work_order_id"],
            "device_id": work_order.get("device_id", "UNKNOWN"),
            **work_order,
        }
        await container.upsert_item(doc)

    async def save_telemetry(self, reading: dict) -> None:
        """Persist a single telemetry reading (30-day TTL on container)."""
        container = await self._container("telemetry")
        doc = {
            "id": f"{reading['device_id']}-{reading.get('timestamp', datetime.now(timezone.utc).isoformat())}",
            "device_id": reading["device_id"],
            **reading,
        }
        await container.upsert_item(doc)

    async def close(self) -> None:
        await self._client.close()
