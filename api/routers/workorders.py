"""
/work-orders router — query and update work orders from Cosmos DB.
"""

import logging
import os
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter()

COSMOS_URL = os.environ.get("COSMOS_ENDPOINT", "")
COSMOS_KEY = os.environ.get("COSMOS_KEY", "")
COSMOS_DB = os.environ.get("COSMOS_DB", "kinetic-core")


@router.get("")
async def list_work_orders(
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    priority: str | None = None,
):
    """List recent work orders, optionally filtered by status or priority."""
    if not COSMOS_URL:
        return {"total": 0, "work_orders": []}

    from azure.cosmos.aio import CosmosClient
    async with CosmosClient(COSMOS_URL, credential=COSMOS_KEY) as client:
        db = client.get_database_client(COSMOS_DB)
        container = db.get_container_client("work-orders")

        query = "SELECT TOP @limit * FROM c"
        params = [{"name": "@limit", "value": limit}]
        filters = []
        if status:
            filters.append("c.status = @status")
            params.append({"name": "@status", "value": status})
        if priority:
            filters.append("c.priority = @priority")
            params.append({"name": "@priority", "value": priority})
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY c.created_at DESC"

        items = [item async for item in container.query_items(query=query, parameters=params)]
        return {"total": len(items), "work_orders": items}


@router.get("/{work_order_id}")
async def get_work_order(work_order_id: str):
    """Fetch a single work order by ID."""
    if not COSMOS_URL:
        raise HTTPException(status_code=503, detail="Cosmos DB not configured")

    from azure.cosmos.aio import CosmosClient
    async with CosmosClient(COSMOS_URL, credential=COSMOS_KEY) as client:
        db = client.get_database_client(COSMOS_DB)
        container = db.get_container_client("work-orders")
        try:
            item = await container.read_item(item=work_order_id, partition_key=work_order_id)
            return item
        except Exception:
            raise HTTPException(status_code=404, detail=f"Work order {work_order_id} not found")


@router.patch("/{work_order_id}/status")
async def update_work_order_status(work_order_id: str, new_status: str):
    """Update the status of a work order (e.g., IN_PROGRESS, COMPLETED)."""
    allowed = {"DISPATCHED", "IN_PROGRESS", "COMPLETED", "CANCELLED"}
    if new_status not in allowed:
        raise HTTPException(status_code=422, detail=f"Status must be one of {allowed}")

    if not COSMOS_URL:
        raise HTTPException(status_code=503, detail="Cosmos DB not configured")

    from azure.cosmos.aio import CosmosClient
    async with CosmosClient(COSMOS_URL, credential=COSMOS_KEY) as client:
        db = client.get_database_client(COSMOS_DB)
        container = db.get_container_client("work-orders")
        try:
            item = await container.read_item(item=work_order_id, partition_key=work_order_id)
            item["status"] = new_status
            await container.replace_item(item=work_order_id, body=item)
            return {"work_order_id": work_order_id, "status": new_status}
        except Exception:
            raise HTTPException(status_code=404, detail=f"Work order {work_order_id} not found")
