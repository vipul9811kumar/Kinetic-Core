"""Pydantic models — the single source of truth for all API request/response shapes."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SafetyDecision(str, Enum):
    GO = "GO"
    NO_GO = "NO_GO"
    GO_WITH_CONDITIONS = "GO_WITH_CONDITIONS"


class IncidentOutcome(str, Enum):
    NO_FAULT = "NO_FAULT"
    BLOCKED_BY_SAFETY = "BLOCKED_BY_SAFETY"
    WORK_ORDER_DISPATCHED = "WORK_ORDER_DISPATCHED"
    IN_PROGRESS = "IN_PROGRESS"


# ── Telemetry ──────────────────────────────────────────────────────────────────

class SensorReadings(BaseModel):
    temperature_celsius: float = Field(..., ge=-10, le=120)
    voltage_v: float = Field(..., ge=0, le=600)
    current_a: float = Field(..., ge=0, le=100)
    vibration_mm_s: float = Field(..., ge=0, le=50)
    coolant_flow_lpm: float = Field(..., ge=0, le=500)
    ambient_temp_celsius: float = Field(..., ge=-10, le=60)
    power_factor: float = Field(..., ge=0, le=1)
    rpm: int = Field(..., ge=0, le=4000)


class FaultFlags(BaseModel):
    thermal_warning: bool = False
    flow_deviation: bool = False
    vibration_alert: bool = False
    voltage_anomaly: bool = False


class DeviceMetadata(BaseModel):
    firmware_version: str
    model: str
    install_date: str
    last_service_date: str | None = None


class TelemetryEvent(BaseModel):
    device_id: str = Field(..., pattern=r"^KCX-[A-Z]{3}-[0-9]{4}$")
    facility_id: str
    rack_id: str
    timestamp: datetime
    readings: SensorReadings
    fault_flags: FaultFlags = Field(default_factory=FaultFlags)
    metadata: DeviceMetadata


class TelemetryBatch(BaseModel):
    events: list[TelemetryEvent] = Field(..., min_length=1, max_length=1000)


# ── Agent Pipeline ─────────────────────────────────────────────────────────────

class AgentRunRequest(BaseModel):
    device_id: str
    telemetry_window: list[TelemetryEvent]
    scenario_hint: str | None = None


class DiagnosticResult(BaseModel):
    agent: str = "DiagnosticLead"
    incident_id: str
    device_id: str
    analyzed_at: datetime
    fault_code: str | None
    fault_description: str
    severity: SeverityLevel
    root_cause: str | None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    reasoning: str = ""
    llm_invoked: bool
    prompt_version: str = "v1.2"


class RepairStep(BaseModel):
    step: int
    action: str
    source_section: str = ""
    safety_critical: bool = False


class PartRequired(BaseModel):
    part_number: str
    part_name: str
    quantity: int = 1


class LibrarianResult(BaseModel):
    agent: str = "TechnicalLibrarian"
    incident_id: str
    fault_code: str
    repair_steps: list[RepairStep]
    parts_list: list[PartRequired]
    estimated_duration_minutes: int
    team_size: int = 2
    tools_required: list[str] = []
    safety_prerequisites: list[str] = []
    source_citations: list[str] = []
    faithfulness_score: float = Field(0.0, ge=0.0, le=1.0)
    requires_human_review: bool = False


class AuditResult(BaseModel):
    agent: str = "SafetyAuditor"
    incident_id: str
    decision: SafetyDecision
    reason: str
    conditions: list[str] = []
    ppe_required: str = ""
    voltage_checked: float
    arc_flash_rating: str
    hard_rule_triggered: bool = False


# ── Incidents ──────────────────────────────────────────────────────────────────

class SafetyClearance(BaseModel):
    approved_by: str
    approved_at: datetime
    voltage_at_approval: float | None
    arc_flash_rating: str | None


class WorkOrder(BaseModel):
    work_order_id: str
    incident_id: str
    created_at: datetime
    priority: SeverityLevel
    fault_code: str
    fault_description: str
    device_id: str | None
    repair_steps: list[RepairStep]
    parts_required: list[PartRequired]
    estimated_duration_minutes: int
    safety_clearance: SafetyClearance
    status: str = "DISPATCHED"
    source_citations: list[str] = []


class IncidentRecord(BaseModel):
    incident_id: str
    started_at: datetime
    resolved_at: datetime | None
    device_id: str
    outcome: IncidentOutcome
    work_order_id: str | None = None
    stages: dict[str, Any] = {}


class IncidentListItem(BaseModel):
    incident_id: str
    started_at: datetime
    device_id: str
    outcome: IncidentOutcome
    severity: SeverityLevel | None
    work_order_id: str | None


class IncidentListResponse(BaseModel):
    total: int
    incidents: list[IncidentListItem]
