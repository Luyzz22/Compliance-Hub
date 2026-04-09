"""Board-level KPI aggregation for executive reporting (Phase 3)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models_db import (
    AISystemTable,
    AuditLogTable,
    ComplianceScoreDB,
)

logger = logging.getLogger(__name__)

# Norm weights for overall compliance score (extensible)
NORM_WEIGHTS: dict[str, float] = {
    "eu_ai_act": 0.30,
    "iso_42001": 0.20,
    "nis2": 0.25,
    "dsgvo": 0.25,
}

UPCOMING_DEADLINES = [
    {
        "deadline": "2026-08-02",
        "norm": "EU AI Act",
        "description": "EU AI Act — Vollständige Anwendbarkeit für Hochrisiko-KI-Systeme",
    },
    {
        "deadline": "2026-12-31",
        "norm": "ISO 42001",
        "description": "ISO 42001 — Empfohlene Zertifizierungsfrist (branchenabhängig)",
    },
]


def compute_overall_compliance_score(session: Session, tenant_id: str) -> dict:
    """Return weighted compliance score from latest per-norm snapshots."""
    rows = (
        session.execute(
            select(ComplianceScoreDB)
            .where(
                ComplianceScoreDB.tenant_id == tenant_id,
                ComplianceScoreDB.score_type == "norm",
            )
            .order_by(ComplianceScoreDB.created_at_utc.desc())
        )
        .scalars()
        .all()
    )
    seen: dict[str, ComplianceScoreDB] = {}
    for r in rows:
        if r.norm and r.norm not in seen:
            seen[r.norm] = r

    total_weight = 0.0
    weighted_sum = 0.0
    norm_scores = []
    for norm, weight in NORM_WEIGHTS.items():
        row = seen.get(norm)
        val = row.score_value if row else 0.0
        weighted_sum += val * weight
        total_weight += weight
        norm_scores.append({"norm": norm, "score": val, "weight": weight})

    overall = round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0
    return {
        "overall_score": overall,
        "norm_scores": norm_scores,
        "computed_at": datetime.now(UTC).isoformat(),
    }


def count_high_risk_ai_systems(session: Session, tenant_id: str) -> int:
    """Count AI systems classified as high-risk for the tenant."""
    result = session.execute(
        select(func.count())
        .select_from(AISystemTable)
        .where(
            AISystemTable.tenant_id == tenant_id,
            AISystemTable.risk_level == "high",
        )
    )
    return result.scalar() or 0


def get_top_findings(session: Session, tenant_id: str, limit: int = 5) -> list[dict]:
    """Return top-N open findings sorted by recency."""
    rows = (
        session.execute(
            select(AuditLogTable)
            .where(
                AuditLogTable.tenant_id == tenant_id,
                AuditLogTable.action.in_(["finding_created", "compliance_gap_identified"]),
            )
            .order_by(AuditLogTable.created_at_utc.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "created_at": r.created_at_utc.isoformat() if r.created_at_utc else None,
        }
        for r in rows
    ]


def get_incident_statistics(session: Session, tenant_id: str) -> dict:
    """Aggregate NIS2/DSGVO incident stats."""
    from app.models_db import NIS2IncidentTable

    total = (
        session.execute(
            select(func.count())
            .select_from(NIS2IncidentTable)
            .where(NIS2IncidentTable.tenant_id == tenant_id)
        ).scalar()
        or 0
    )

    open_count = (
        session.execute(
            select(func.count())
            .select_from(NIS2IncidentTable)
            .where(
                NIS2IncidentTable.tenant_id == tenant_id,
                NIS2IncidentTable.workflow_status == "detected",
            )
        ).scalar()
        or 0
    )

    closed_count = (
        session.execute(
            select(func.count())
            .select_from(NIS2IncidentTable)
            .where(
                NIS2IncidentTable.tenant_id == tenant_id,
                NIS2IncidentTable.closed_at.isnot(None),
            )
        ).scalar()
        or 0
    )

    return {
        "total": total,
        "open": open_count,
        "closed": closed_count,
        "escalated": total - open_count - closed_count,
    }


def get_trend_data(session: Session, tenant_id: str) -> list[dict]:
    """Return quarterly compliance score trend (latest 4 snapshots)."""
    rows = (
        session.execute(
            select(ComplianceScoreDB)
            .where(
                ComplianceScoreDB.tenant_id == tenant_id,
                ComplianceScoreDB.score_type == "overall",
            )
            .order_by(ComplianceScoreDB.created_at_utc.desc())
            .limit(4)
        )
        .scalars()
        .all()
    )
    return [
        {"period": r.period, "score": r.score_value, "created_at": r.created_at_utc.isoformat()}
        for r in reversed(rows)
    ]


def build_board_kpi_report(session: Session, tenant_id: str) -> dict:
    """Assemble complete board-level KPI report."""
    return {
        "tenant_id": tenant_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "compliance_score": compute_overall_compliance_score(session, tenant_id),
        "high_risk_ai_systems": count_high_risk_ai_systems(session, tenant_id),
        "top_findings": get_top_findings(session, tenant_id),
        "incident_statistics": get_incident_statistics(session, tenant_id),
        "trend_data": get_trend_data(session, tenant_id),
        "upcoming_deadlines": UPCOMING_DEADLINES,
    }


def persist_compliance_score(
    session: Session,
    *,
    tenant_id: str,
    score_type: str,
    score_value: float,
    norm: str | None = None,
    weight: float = 1.0,
    period: str = "",
    details: dict | None = None,
) -> ComplianceScoreDB:
    """Create and persist a compliance score snapshot."""
    now = datetime.now(UTC)
    quarter = (now.month - 1) // 3 + 1
    row = ComplianceScoreDB(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        score_type=score_type,
        norm=norm,
        score_value=score_value,
        weight=weight,
        details_json=json.dumps(details) if details else None,
        period=period or f"{now.year}-Q{quarter}",
        created_at_utc=now,
    )
    session.add(row)
    session.flush()
    return row
