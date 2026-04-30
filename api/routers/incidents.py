"""
/incidents router — query incident records from Cosmos DB.
"""

import logging
import os
from fastapi import APIRouter, HTTPException, Query

from api.models.schemas import IncidentListResponse

logger = logging.getLogger(__name__)
router = APIRouter()

COSMOS_URL = os.environ.get("COSMOS_ENDPOINT", "")
COSMOS_KEY = os.environ.get("COSMOS_KEY", "")
COSMOS_DB = os.environ.get("COSMOS_DB", "kinetic-core")


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    limit: int = Query(20, ge=1, le=100),
    device_id: str | None = None,
    outcome: str | None = None,
):
    """List recent incidents, optionally filtered by device or outcome."""
    if not COSMOS_URL:
        return IncidentListResponse(total=0, incidents=[])

    from azure.cosmos.aio import CosmosClient
    async with CosmosClient(COSMOS_URL, credential=COSMOS_KEY) as client:
        db = client.get_database_client(COSMOS_DB)
        container = db.get_container_client("incidents")

        query = "SELECT TOP @limit c.incident_id, c.started_at, c.device_id, c.outcome, c.work_order_id FROM c"
        params = [{"name": "@limit", "value": limit}]
        filters = []
        if device_id:
            filters.append("c.device_id = @device_id")
            params.append({"name": "@device_id", "value": device_id})
        if outcome:
            filters.append("c.outcome = @outcome")
            params.append({"name": "@outcome", "value": outcome})
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY c.started_at DESC"

        items = [item async for item in container.query_items(query=query, parameters=params)]
        return IncidentListResponse(total=len(items), incidents=items)


@router.get("/{incident_id}")
async def get_incident(incident_id: str):
    """Fetch the full lifecycle record for a single incident including all agent traces."""
    if not COSMOS_URL:
        raise HTTPException(status_code=503, detail="Cosmos DB not configured")

    from azure.cosmos.aio import CosmosClient
    async with CosmosClient(COSMOS_URL, credential=COSMOS_KEY) as client:
        db = client.get_database_client(COSMOS_DB)
        container = db.get_container_client("incidents")
        try:
            item = await container.read_item(item=incident_id, partition_key=incident_id)
            return item
        except Exception:
            raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
