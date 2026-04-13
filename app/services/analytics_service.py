from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models_db import (
    AuditAlertDB,
    AuditLogTable,
    ComplianceControlDB,
    ComplianceFrameworkDB,
    ComplianceRequirementControlLinkDB,
    ComplianceRequirementDB,
    TrustCenterAccessLogDB,
)

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300


def _ttl_cache(ttl: int = _CACHE_TTL_SECONDS):
    """Decorator that caches function results with a time-to-live expiry."""

    def decorator(fn):
        _cache: dict[tuple, tuple[float, Any]] = {}
        _lock = threading.Lock()

        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = args + tuple(sorted(kwargs.items()))
            now = time.monotonic()
            with _lock:
                if key in _cache:
                    ts, value = _cache[key]
                    if now - ts < ttl:
                        return value
            result = fn(*args, **kwargs)
            with _lock:
                _cache[key] = (now, result)
            return result

        wrapper.cache = _cache  # type: ignore[attr-defined]
        wrapper.cache_clear = lambda: _cache.clear()  # type: ignore[attr-defined]
        return wrapper

    return decorator


def get_compliance_score(session: Session, tenant_id: str) -> dict:
    """Return overall compliance score as percentage of implemented/verified controls."""
    total = (
        session.query(func.count(ComplianceControlDB.id))
        .filter(ComplianceControlDB.tenant_id == tenant_id)
        .scalar()
    ) or 0

    implemented = (
        session.query(func.count(ComplianceControlDB.id))
        .filter(
            ComplianceControlDB.tenant_id == tenant_id,
            ComplianceControlDB.status.in_(["implemented", "verified"]),
        )
        .scalar()
    ) or 0

    score = round((implemented / total) * 100, 2) if total > 0 else 0.0

    return {
        "score": score,
        "total_controls": total,
        "implemented_controls": implemented,
    }


def get_kpi_summary(
    session: Session, tenant_id: str, period_days: int = 30
) -> dict:
    """Return all KPIs in a single call."""
    compliance = get_compliance_score(session, tenant_id)

    open_risks = (
        session.query(func.count(AuditAlertDB.id))
        .filter(
            AuditAlertDB.tenant_id == tenant_id,
            AuditAlertDB.severity.in_(["CRITICAL", "HIGH"]),
            AuditAlertDB.resolved.is_(False),
        )
        .scalar()
    ) or 0

    since = datetime.now(UTC) - timedelta(days=period_days)
    trust_center_accesses = (
        session.query(func.count(TrustCenterAccessLogDB.id))
        .filter(
            TrustCenterAccessLogDB.tenant_id == tenant_id,
            TrustCenterAccessLogDB.created_at_utc >= since,
        )
        .scalar()
    ) or 0

    return {
        "compliance_score": compliance,
        "open_risks": open_risks,
        "trust_center_accesses": trust_center_accesses,
        "upcoming_deadlines": [],
    }


def get_framework_coverage(session: Session, tenant_id: str) -> list[dict]:
    """Return per-framework requirement coverage breakdown for a tenant."""
    frameworks = session.query(ComplianceFrameworkDB).all()

    tenant_control_ids = [
        cid
        for (cid,) in session.query(ComplianceControlDB.id).filter(
            ComplianceControlDB.tenant_id == tenant_id,
        )
    ]

    results: list[dict] = []
    for fw in frameworks:
        requirements = (
            session.query(ComplianceRequirementDB)
            .filter(ComplianceRequirementDB.framework_id == fw.id)
            .all()
        )
        total_requirements = len(requirements)
        req_ids = [r.id for r in requirements]

        status_counts: dict[str, int] = defaultdict(int)

        if req_ids and tenant_control_ids:
            links = (
                session.query(ComplianceRequirementControlLinkDB)
                .filter(
                    ComplianceRequirementControlLinkDB.requirement_id.in_(req_ids),
                    ComplianceRequirementControlLinkDB.control_id.in_(
                        tenant_control_ids
                    ),
                )
                .all()
            )

            linked_req_control: dict[int, list[str]] = defaultdict(list)
            for link in links:
                control = (
                    session.query(ComplianceControlDB)
                    .filter(ComplianceControlDB.id == link.control_id)
                    .first()
                )
                if control:
                    linked_req_control[link.requirement_id].append(control.status)

            for req_id in req_ids:
                statuses = linked_req_control.get(req_id, [])
                if not statuses:
                    continue
                if any(s in ("implemented", "verified") for s in statuses):
                    status_counts["covered"] += 1
                elif any(s == "planned" for s in statuses):
                    status_counts["planned"] += 1
                elif any(s == "not_applicable" for s in statuses):
                    status_counts["not_applicable"] += 1
                else:
                    status_counts["partial"] += 1

        results.append(
            {
                "framework": fw.name,
                "framework_key": fw.key,
                "total_requirements": total_requirements,
                "covered": status_counts["covered"],
                "partial": status_counts["partial"],
                "planned": status_counts["planned"],
                "not_applicable": status_counts["not_applicable"],
            }
        )

    return results


def get_risk_matrix(session: Session, tenant_id: str) -> dict:
    """Return unresolved alert counts grouped by severity."""
    rows = (
        session.query(
            AuditAlertDB.severity,
            func.count(AuditAlertDB.id),
        )
        .filter(
            AuditAlertDB.tenant_id == tenant_id,
            AuditAlertDB.resolved.is_(False),
        )
        .group_by(AuditAlertDB.severity)
        .all()
    )

    matrix = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for severity, count in rows:
        key = severity.lower()
        if key in matrix:
            matrix[key] = count

    matrix["total"] = sum(matrix.values())
    return matrix


def get_activity_feed(
    session: Session, tenant_id: str, limit: int = 10
) -> list[dict]:
    """Return the latest audit log entries for a tenant."""
    entries = (
        session.query(AuditLogTable)
        .filter(AuditLogTable.tenant_id == tenant_id)
        .order_by(AuditLogTable.created_at_utc.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": entry.id,
            "actor": entry.actor,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "created_at": entry.created_at_utc.isoformat()
            if entry.created_at_utc
            else None,
            "outcome": entry.outcome,
        }
        for entry in entries
    ]
