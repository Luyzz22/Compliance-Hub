"""AI-Governance Incident-Übersicht für Board-Drilldown (NIS2 Art. 21/23, ISO 42001)."""

from __future__ import annotations

from app.incident_models import (
    AIIncidentBySystemEntry,
    AIIncidentOverview,
    BySeverityEntry,
    IncidentSeverity,
)
from app.repositories.ai_systems import AISystemRepository
from app.repositories.incidents import IncidentRepository


def compute_ai_incident_overview(
    tenant_id: str,
    incident_repository: IncidentRepository,
) -> AIIncidentOverview:
    """Aggregierte Incident-Übersicht für GET /api/v1/ai-governance/incidents/overview."""
    total, open_count, major, mtta, mttr, by_severity = incident_repository.aggregate_overview(
        tenant_id
    )
    by_severity_entries = [
        BySeverityEntry(severity=IncidentSeverity(s), count=c) for s, c in by_severity
    ]
    return AIIncidentOverview(
        tenant_id=tenant_id,
        total_incidents_last_12_months=total,
        open_incidents=open_count,
        major_incidents_last_12_months=major,
        mean_time_to_ack_hours=round(mtta, 2) if mtta is not None else None,
        mean_time_to_recover_hours=round(mttr, 2) if mttr is not None else None,
        by_severity=by_severity_entries,
    )


def compute_ai_incidents_by_system(
    tenant_id: str,
    incident_repository: IncidentRepository,
    ai_system_repository: AISystemRepository,
) -> list[AIIncidentBySystemEntry]:
    """Pro-System-Incident-Liste für GET /api/v1/ai-governance/incidents/by-system."""
    rows = incident_repository.aggregate_by_system(tenant_id)
    entries: list[AIIncidentBySystemEntry] = []
    for ai_system_id, incident_count, last_incident_at in rows:
        ai_system = ai_system_repository.get_by_id(tenant_id, ai_system_id)
        name = ai_system.name if ai_system else ai_system_id
        entries.append(
            AIIncidentBySystemEntry(
                ai_system_id=ai_system_id,
                ai_system_name=name,
                incident_count=incident_count,
                last_incident_at=last_incident_at,
            )
        )

    def _sort_key(e: AIIncidentBySystemEntry) -> tuple[int, float]:
        ts = e.last_incident_at.timestamp() if e.last_incident_at else 0.0
        return (-e.incident_count, ts)

    return sorted(entries, key=_sort_key)
