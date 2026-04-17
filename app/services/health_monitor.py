"""
Operational Resilience — poll internal deep health, persist snapshots, raise incidents.

Scheduling: invoke ``run_operational_health_poll_all_tenants`` from a cron job, systemd timer,
or (optional) APScheduler on app startup — see TODO at bottom. n8n / queue fan-out later.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from uuid import uuid4

from sqlalchemy.orm import Session

from app.governance_taxonomy import GovernanceAuditAction, GovernanceAuditEntity
from app.rbac.roles import EnterpriseRole
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.service_health import ServiceHealthRepository
from app.services.governance_audit import record_governance_audit
from app.services.health_incident_rules import evaluate_health_transition
from app.services.internal_health_core import InternalDeepHealthDTO, compute_internal_deep_health

logger = logging.getLogger(__name__)

_SERVICE_NAMES = ("app", "db", "external_ai_provider")


@dataclass
class OperationalHealthPollResult:
    tenants_processed: int = 0
    snapshots_written: int = 0
    incidents_opened: int = 0
    incidents_resolved: int = 0
    errors: list[str] = field(default_factory=list)


def _status_for_service(dto: InternalDeepHealthDTO, service_name: str) -> str:
    if service_name == "app":
        return dto.app
    if service_name == "db":
        return dto.db
    if service_name == "external_ai_provider":
        return dto.external_ai_provider
    raise ValueError(f"unknown service_name {service_name!r}")


def _audit(
    audit_repo: AuditLogRepository | None,
    *,
    tenant_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: dict,
) -> None:
    if audit_repo is None:
        return
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id="system:operational_health_poller",
        actor_role=EnterpriseRole.AUDITOR,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        outcome="success",
        before=None,
        after=json.dumps(metadata, default=str),
        correlation_id=None,
        metadata=metadata,
        ip_address=None,
        user_agent="operational-health-monitor",
    )


def run_operational_health_poll_for_tenant(
    session: Session,
    tenant_id: str,
    audit_repo: AuditLogRepository | None,
    *,
    dto: InternalDeepHealthDTO | None = None,
) -> OperationalHealthPollResult:
    """
    Persist one poll wave for a single tenant (shared infra health replicated per tenant_id).

    Platform health is identical across tenants in this MVP; per-tenant rows keep RLS-ready
    shapes and tenant-scoped dashboards without leaking cross-tenant reads later.
    """
    out = OperationalHealthPollResult()
    repo = ServiceHealthRepository(session)
    dto = dto or compute_internal_deep_health(session)
    raw_payload = {
        "app": dto.app,
        "db": dto.db,
        "external_ai_provider": dto.external_ai_provider,
        "timestamp": dto.timestamp.isoformat(),
    }
    poll_run_id = str(uuid4())
    checked_at = dto.timestamp

    incidents_opened = 0
    incidents_resolved = 0

    for service_name in _SERVICE_NAMES:
        new_status = _status_for_service(dto, service_name)
        previous = repo.last_status_for_service(tenant_id, service_name)
        snap_id = repo.insert_snapshot(
            tenant_id=tenant_id,
            poll_run_id=poll_run_id,
            service_name=service_name,
            status=new_status,
            checked_at=checked_at,
            raw_payload=raw_payload,
        )
        out.snapshots_written += 1

        decision = evaluate_health_transition(previous, new_status)

        if decision.resolve_open:
            n = repo.resolve_open_incidents_for_service(tenant_id, service_name, checked_at)
            incidents_resolved += n
            if n and audit_repo is not None:
                _audit(
                    audit_repo,
                    tenant_id=tenant_id,
                    action=GovernanceAuditAction.SERVICE_HEALTH_INCIDENT_RESOLVED.value,
                    entity_type=GovernanceAuditEntity.SERVICE_HEALTH_INCIDENT.value,
                    entity_id=f"{tenant_id}:{service_name}",
                    metadata={
                        "service_name": service_name,
                        "resolved_at": checked_at.isoformat(),
                        "rows_closed": n,
                        "source": "internal_health_poll",
                    },
                )

        instr = decision.open_incident
        if instr is not None:
            iid = repo.insert_incident(
                tenant_id=tenant_id,
                service_name=service_name,
                previous_status=previous,
                current_status=new_status,
                severity=instr.severity,
                source="internal_health_poll",
                detected_at=checked_at,
                triggering_snapshot_id=snap_id,
                title=instr.title_de,
                summary=instr.summary_de,
            )
            incidents_opened += 1
            _audit(
                audit_repo,
                tenant_id=tenant_id,
                action=GovernanceAuditAction.SERVICE_HEALTH_INCIDENT_DETECTED.value,
                entity_type=GovernanceAuditEntity.SERVICE_HEALTH_INCIDENT.value,
                entity_id=iid,
                metadata={
                    "service_name": service_name,
                    "previous_status": previous,
                    "current_status": new_status,
                    "severity": instr.severity,
                    "source": "internal_health_poll",
                },
            )

    out.incidents_opened = incidents_opened
    out.incidents_resolved = incidents_resolved
    out.tenants_processed = 1

    _audit(
        audit_repo,
        tenant_id=tenant_id,
        action=GovernanceAuditAction.SERVICE_HEALTH_POLL_COMPLETED.value,
        entity_type=GovernanceAuditEntity.SERVICE_HEALTH_SNAPSHOT.value,
        entity_id=poll_run_id,
        metadata={
            "poll_run_id": poll_run_id,
            "snapshots": len(_SERVICE_NAMES),
            "incidents_opened": incidents_opened,
            "incidents_resolved": incidents_resolved,
            "source": "internal_health_poll",
        },
    )

    return out


def run_operational_health_poll_all_tenants(
    session: Session,
    audit_repo: AuditLogRepository | None,
) -> OperationalHealthPollResult:
    """Poll once, write snapshots (+ incidents) for every registered tenant."""
    aggregate = OperationalHealthPollResult()
    repo = ServiceHealthRepository(session)
    tenant_ids = repo.list_tenant_ids()
    if not tenant_ids:
        logger.info("operational health poll: no tenants registered — skipping")
        return aggregate

    dto = compute_internal_deep_health(session)
    for tid in tenant_ids:
        try:
            part = run_operational_health_poll_for_tenant(session, tid, audit_repo, dto=dto)
            aggregate.tenants_processed += part.tenants_processed
            aggregate.snapshots_written += part.snapshots_written
            aggregate.incidents_opened += part.incidents_opened
            aggregate.incidents_resolved += part.incidents_resolved
        except Exception as exc:  # noqa: BLE001 — log and continue other tenants
            logger.exception("operational health poll failed for tenant %s", tid)
            aggregate.errors.append(f"{tid}: {exc!r}")
    return aggregate


# TODO(phase-2): optional APScheduler job:
#   from apscheduler.schedulers.background import BackgroundScheduler
#   scheduler.add_job(
#       lambda: run_poll_in_request_context(),
#       "interval",
#       minutes=int(os.getenv("OPERATIONAL_HEALTH_POLL_MINUTES", "5")),
#   )
# TODO(phase-2): push webhook to n8n on critical incident for ticket creation.
