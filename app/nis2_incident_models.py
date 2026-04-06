from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class NIS2IncidentType(StrEnum):
    """ENISA Taxonomy incident types."""

    RANSOMWARE = "ransomware"
    DDOS = "ddos"
    SUPPLY_CHAIN = "supply_chain"
    DATA_BREACH = "data_breach"
    PHISHING = "phishing"
    INSIDER_THREAT = "insider_threat"
    MALWARE = "malware"
    SYSTEM_FAILURE = "system_failure"
    OTHER = "other"


class NIS2WorkflowStatus(StrEnum):
    """NIS2 Art. 21 compliant workflow states."""

    DETECTED = "detected"
    CONTAINED = "contained"
    ERADICATED = "eradicated"
    RECOVERED = "recovered"
    CLOSED = "closed"


VALID_TRANSITIONS: dict[NIS2WorkflowStatus, list[NIS2WorkflowStatus]] = {
    NIS2WorkflowStatus.DETECTED: [NIS2WorkflowStatus.CONTAINED],
    NIS2WorkflowStatus.CONTAINED: [NIS2WorkflowStatus.ERADICATED],
    NIS2WorkflowStatus.ERADICATED: [NIS2WorkflowStatus.RECOVERED],
    NIS2WorkflowStatus.RECOVERED: [NIS2WorkflowStatus.CLOSED],
    NIS2WorkflowStatus.CLOSED: [],
}


class NIS2IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    incident_type: NIS2IncidentType
    severity: str = Field(pattern=r"^(low|medium|high|critical)$")
    summary: str = Field(min_length=1, max_length=5000)
    affected_systems: list[str] = Field(default_factory=list)
    kritis_relevant: bool = False
    personal_data_affected: bool = False
    estimated_impact: str | None = None


class NIS2IncidentResponse(BaseModel):
    id: str
    tenant_id: str
    title: str
    incident_type: NIS2IncidentType
    severity: str
    workflow_status: NIS2WorkflowStatus
    summary: str
    affected_systems: list[str]
    kritis_relevant: bool
    personal_data_affected: bool
    estimated_impact: str | None = None
    bsi_notification_deadline: datetime | None = None
    bsi_report_deadline: datetime | None = None
    detected_at: datetime
    contained_at: datetime | None = None
    eradicated_at: datetime | None = None
    recovered_at: datetime | None = None
    closed_at: datetime | None = None
    created_by: str | None = None


class NIS2IncidentTransition(BaseModel):
    target_status: NIS2WorkflowStatus
    notes: str | None = None
