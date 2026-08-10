from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator


def _as_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC so comparisons never raise."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


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


class NIS2DeadlineBasis(StrEnum):
    """Which timestamp the regulatory deadlines were anchored to."""

    #: Anchored to the moment the entity became aware of the incident (NIS2 Art. 23).
    AWARENESS = "awareness"
    #: Legacy/backfilled rows where only the record-creation time was known.
    ENTRY_FALLBACK = "entry_fallback"
    #: At least one deadline on this record was set by hand rather than computed.
    #:
    #: The marker is record-level, not per deadline: a partial override still means the
    #: record's deadlines can no longer be read as purely derived from awareness. Which
    #: individual deadlines were changed, by whom and why is recorded in the audit trail
    #: under ``NIS2_INCIDENT_DEADLINE_OVERRIDE``.
    MANUAL_OVERRIDE = "manual_override"


class NIS2IncidentCreate(BaseModel):
    """
    Incident intake.

    ``became_aware_at`` is mandatory because NIS2 Art. 23 runs the 24h/72h/one-month
    cascade from the moment the entity *became aware* of the significant incident — not
    from the moment somebody typed it into a tool. Anchoring on record creation would
    silently report "within deadline" for an incident whose deadline already expired.
    """

    title: str = Field(min_length=1, max_length=500)
    incident_type: NIS2IncidentType
    severity: str = Field(pattern=r"^(low|medium|high|critical)$")
    summary: str = Field(min_length=1, max_length=5000)
    affected_systems: list[str] = Field(default_factory=list)
    kritis_relevant: bool = False
    personal_data_affected: bool = False
    estimated_impact: str | None = None
    became_aware_at: datetime = Field(
        description=(
            "Zeitpunkt der Kenntniserlangung (UTC). Ankerpunkt für alle Meldefristen "
            "nach NIS2 Art. 23."
        ),
    )
    detected_at: datetime | None = Field(
        default=None,
        description=(
            "Optionaler Zeitpunkt der technischen Detektion. Kann vor der "
            "Kenntniserlangung der verantwortlichen Stelle liegen."
        ),
    )

    @model_validator(mode="after")
    def validate_timestamps(self) -> Self:
        aware = _as_utc(self.became_aware_at)
        now = datetime.now(UTC)
        if aware > now + timedelta(minutes=5):
            raise ValueError("became_aware_at must not be in the future")
        if self.detected_at is not None and _as_utc(self.detected_at) > aware:
            raise ValueError("detected_at must not be after became_aware_at")
        return self


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
    final_report_deadline: datetime | None = None
    notification_deadline_overdue: bool = False
    report_deadline_overdue: bool = False
    final_report_deadline_overdue: bool = False
    became_aware_at: datetime | None = None
    deadline_basis: NIS2DeadlineBasis = NIS2DeadlineBasis.AWARENESS
    detected_at: datetime
    contained_at: datetime | None = None
    eradicated_at: datetime | None = None
    recovered_at: datetime | None = None
    closed_at: datetime | None = None
    created_by: str | None = None


class NIS2IncidentTransition(BaseModel):
    target_status: NIS2WorkflowStatus
    notes: str | None = None


class NIS2IncidentDeadlinesOverride(BaseModel):
    """Regulatory deadline override (audited). At least one deadline must be supplied."""

    bsi_notification_deadline: datetime | None = None
    bsi_report_deadline: datetime | None = None
    final_report_deadline: datetime | None = None
    reason: str = Field(min_length=8, max_length=2000)

    @model_validator(mode="after")
    def at_least_one_deadline(self) -> Self:
        if (
            self.bsi_notification_deadline is None
            and self.bsi_report_deadline is None
            and self.final_report_deadline is None
        ):
            raise ValueError("At least one deadline must be provided")
        return self
