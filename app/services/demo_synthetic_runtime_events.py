"""Deterministische synthetische ai_runtime_events für Demo/Pilot (keine PII, Katalog-konform)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import NAMESPACE_DNS, uuid5

from app.models_db import AiRuntimeEventTable
from app.repositories.ai_runtime_events import AiRuntimeEventRepository

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

SYNTHETIC_RUNTIME_SOURCE = "synthetic_demo_seed"


def _occurred_at_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _per_system_event_prefix(*, tag: str, ai_system_id: str) -> str:
    """Kurz-Präfix pro System: UNIQUE (tenant_id, source, source_event_id) ist global je Quelle."""
    t = "".join(c if c.isalnum() else "" for c in tag.lower())[:8] or "gov"
    h = str(uuid5(NAMESPACE_DNS, f"ch:synthetic_rt:{ai_system_id}"))[:10]
    return f"synthetic-{t}-{h}"


def synthetic_governance_demo_runtime_specs(
    *,
    now: datetime,
    tag: str,
    ai_system_id: str,
) -> list[dict[str, object]]:
    """
    16 Events über ~90 Tage: Heartbeats, Snapshots, Incidents (mittel, zeitlich zurückliegend),
    Deployment-Änderungen, ein Drift-Breach – für glaubwürdiges OAMI „Medium“.
    """
    prefix = _per_system_event_prefix(tag=tag, ai_system_id=ai_system_id)

    def oid(suffix: str) -> str:
        return f"{prefix}-{suffix}"[:128]

    return [
        {
            "source_event_id": oid("hb-recent"),
            "event_type": "heartbeat",
            "occurred_at": now - timedelta(days=1),
        },
        {
            "source_event_id": oid("hb-3d"),
            "event_type": "heartbeat",
            "occurred_at": now - timedelta(days=3),
        },
        {
            "source_event_id": oid("snap-drift"),
            "event_type": "metric_snapshot",
            "metric_key": "drift_score",
            "value": 0.07,
            "occurred_at": now - timedelta(days=4),
        },
        {
            "source_event_id": oid("snap-err"),
            "event_type": "metric_snapshot",
            "metric_key": "error_rate",
            "value": 0.04,
            "occurred_at": now - timedelta(days=6),
        },
        {
            "source_event_id": oid("inc-med"),
            "event_type": "incident",
            "severity": "medium",
            "incident_code": "DEMO_LATENCY_SPIKE",
            "occurred_at": now - timedelta(days=8),
        },
        {
            "source_event_id": oid("deploy-1"),
            "event_type": "deployment_change",
            "occurred_at": now - timedelta(days=10),
        },
        {
            "source_event_id": oid("breach-drift"),
            "event_type": "metric_threshold_breach",
            "metric_key": "drift_score",
            "value": 0.19,
            "threshold_breached": True,
            "occurred_at": now - timedelta(days=14),
        },
        {
            "source_event_id": oid("inc-low"),
            "event_type": "incident",
            "severity": "low",
            "incident_code": "DEMO_FALSE_POSITIVE",
            "occurred_at": now - timedelta(days=18),
        },
        {
            "source_event_id": oid("snap-drift-2"),
            "event_type": "metric_snapshot",
            "metric_key": "drift_score",
            "value": 0.11,
            "occurred_at": now - timedelta(days=22),
        },
        {
            "source_event_id": oid("hb-25d"),
            "event_type": "heartbeat",
            "occurred_at": now - timedelta(days=25),
        },
        {
            "source_event_id": oid("deploy-2"),
            "event_type": "deployment_change",
            "occurred_at": now - timedelta(days=30),
        },
        {
            "source_event_id": oid("inc-med-old"),
            "event_type": "incident",
            "severity": "medium",
            "incident_code": "DEMO_API_TIMEOUT",
            "occurred_at": now - timedelta(days=40),
        },
        {
            "source_event_id": oid("snap-safety"),
            "event_type": "metric_snapshot",
            "metric_key": "safety_violation_count",
            "value": 0.0,
            "occurred_at": now - timedelta(days=48),
        },
        {
            "source_event_id": oid("hb-55d"),
            "event_type": "heartbeat",
            "occurred_at": now - timedelta(days=55),
        },
        {
            "source_event_id": oid("breach-err"),
            "event_type": "metric_threshold_breach",
            "metric_key": "error_rate",
            "value": 0.11,
            "threshold_breached": True,
            "occurred_at": now - timedelta(days=62),
        },
        {
            "source_event_id": oid("deploy-3"),
            "event_type": "deployment_change",
            "occurred_at": now - timedelta(days=78),
        },
    ]


def ensure_synthetic_runtime_events_for_system(
    session: Session,
    tenant_id: str,
    ai_system_id: str,
    *,
    tag: str = "govmat",
) -> int:
    """Fügt fehlende synthetische Events hinzu. Idempotent pro (tenant, source, source_event_id)."""
    repo = AiRuntimeEventRepository(session)
    now = datetime.now(UTC)
    specs = synthetic_governance_demo_runtime_specs(
        now=now,
        tag=tag,
        ai_system_id=ai_system_id,
    )
    inserted = 0
    for spec in specs:
        seid = str(spec["source_event_id"])
        if repo.exists_by_tenant_source_event_id(tenant_id, SYNTHETIC_RUNTIME_SOURCE, seid):
            continue
        row = AiRuntimeEventTable(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            ai_system_id=ai_system_id,
            source=SYNTHETIC_RUNTIME_SOURCE,
            source_event_id=seid,
            event_type=str(spec["event_type"]),
            severity=spec.get("severity"),  # type: ignore[arg-type]
            metric_key=spec.get("metric_key"),  # type: ignore[arg-type]
            incident_code=spec.get("incident_code"),  # type: ignore[arg-type]
            value=spec.get("value"),  # type: ignore[arg-type]
            delta=None,
            threshold_breached=spec.get("threshold_breached"),  # type: ignore[arg-type]
            environment="prod",
            model_version="demo-synthetic",
            occurred_at=_occurred_at_utc(spec["occurred_at"]),
            received_at=now,
            extra={"region": "eu-de", "demo_synthetic": True},
        )
        repo.add(row)
        inserted += 1
    if inserted:
        logger.info(
            "demo_synthetic_runtime_events tenant_id=%s ai_system_id=%s inserted=%d",
            tenant_id,
            ai_system_id,
            inserted,
        )
    return inserted
