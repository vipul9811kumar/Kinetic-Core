"""
Kinetic-Core FastAPI Backend

Endpoints:
  POST /events/telemetry     — receive telemetry batch from IoT processor
  POST /agents/run           — trigger the multi-agent pipeline manually
  GET  /incidents/{id}       — fetch incident lifecycle record
  GET  /incidents            — list recent incidents
  GET  /work-orders          — list work orders
  GET  /health               — liveness probe
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.middleware.logging import RequestLoggingMiddleware
from api.routers import events, agents, incidents, workorders

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Kinetic-Core API starting up")
    yield
    logger.info("Kinetic-Core API shutting down")


app = FastAPI(
    title="Kinetic-Core API",
    description="Autonomous Reliability Engineer for Critical Power Systems",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(incidents.router, prefix="/incidents", tags=["Incidents"])
app.include_router(workorders.router, prefix="/work-orders", tags=["Work Orders"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "service": "kinetic-core-api", "version": "1.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
