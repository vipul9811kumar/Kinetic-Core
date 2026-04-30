"""
/agents router — manually trigger the multi-agent pipeline for a given device + window.
Useful for testing, replays, and the demo dashboard.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from api.models.schemas import AgentRunRequest
from api.routers.events import get_orchestrator
from agents.orchestrator.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/run", status_code=status.HTTP_200_OK)
async def run_agent_pipeline(
    request: AgentRunRequest,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
):
    """
    Manually trigger the full multi-agent pipeline for a telemetry window.
    Returns the complete incident lifecycle trace including all agent reasoning.
    """
    if len(request.telemetry_window) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Telemetry window must contain at least 2 readings for trend analysis",
        )

    window_dicts = [e.model_dump(mode="json") for e in request.telemetry_window]
    try:
        result = await orchestrator.run_incident(window_dicts)
    except Exception as exc:
        logger.error(f"Agent pipeline error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {str(exc)}")

    return result


@router.get("/status")
async def agent_status():
    """Health check for agent subsystem."""
    return {
        "agents": ["DiagnosticLead", "TechnicalLibrarian", "SafetyAuditor", "Orchestrator"],
        "status": "ready",
        "prompt_versions": {
            "diagnostic_lead": "v1.2",
            "technical_librarian": "v1.1",
            "safety_auditor": "v1.0",
        },
    }
