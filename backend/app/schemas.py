from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TargetCreate(BaseModel):
    name: str
    target_type: str = Field(pattern="^(ping|http|dns)$")
    address: str
    interval_seconds: int = 15
    enabled: bool = True
    extra: dict[str, Any] = Field(default_factory=dict)


class TargetRead(BaseModel):
    id: int
    name: str
    target_type: str
    address: str
    interval_seconds: int
    enabled: bool
    extra: dict[str, Any]

    model_config = {"from_attributes": True}


class CheckResultRead(BaseModel):
    id: int
    target_id: int
    status: str
    latency_ms: float | None
    message: str
    details: dict[str, Any]
    created_at: datetime


class IncidentNoteCreate(BaseModel):
    note: str


class IncidentNoteRead(BaseModel):
    id: int
    incident_id: int
    note: str
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentUpdate(BaseModel):
    status: str | None = None
    root_cause: str | None = None


class IncidentRead(BaseModel):
    id: int
    target_id: int
    title: str
    severity: str
    status: str
    root_cause: str | None
    created_at: datetime
    resolved_at: datetime | None
    notes: list[IncidentNoteRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AlertEventRead(BaseModel):
    id: int
    incident_id: int
    channel: str
    subject: str
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SummaryResponse(BaseModel):
    total_targets: int
    up_targets: int
    degraded_targets: int
    down_targets: int
    open_incidents: int
    recent_alerts: int
    uptime_percent_24h: float
    ext_firing: int = 0
    ext_unacked: int = 0
    ext_auto_acked: int = 0


class SimulationToggle(BaseModel):
    target_id: int
    mode: str
    latency_ms: int | None = None
