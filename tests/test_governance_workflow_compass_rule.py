"""Workflow-Rule für kritische Compass-Signale.

Verifiziert die deterministische Materialisierung von "Compass Daten-/
Konfigurationsprüfung"-Tasks auf Basis der jüngsten Compass-Events.

Gilt nur bei wirklich kritischen Fällen (failed-Run oder Confidence < Floor),
um Task-Floods zu vermeiden — daher minimaler Coverage-Fokus.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app
from app.models_db import GovernanceWorkflowEventTable, GovernanceWorkflowTaskTable
from app.services.compliance_compass_service import (
    COMPASS_EVENT_SOURCE_TYPE,
    COMPASS_EVENT_TYPE_COMPLETED,
    COMPASS_EVENT_TYPE_FAILED,
)
from app.services.governance_workflow_service import COMPASS_TASK_CONFIDENCE_FLOOR

client = TestClient(app)


def _h(tid: str) -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-tenant-id": tid}


def _seed_compass_event(
    *,
    tenant_id: str,
    event_type: str,
    confidence: int | None,
    error_type: str | None = None,
    at: datetime | None = None,
) -> None:
    when = at or datetime.now(UTC)
    payload: dict[str, object] = {"model_version": "test"}
    if confidence is not None:
        payload["confidence_0_100"] = confidence
        payload["fusion_index_0_100"] = confidence
        payload["posture"] = "elevated"
    if error_type:
        payload["error_type"] = error_type
        payload["stage"] = "snapshot_pipeline"
    with Session(engine) as s:
        s.add(
            GovernanceWorkflowEventTable(
                id=f"evt-{tenant_id}-{when.timestamp()}",
                tenant_id=tenant_id,
                at_utc=when,
                event_type=event_type,
                severity="error" if error_type else "info",
                ref_task_id=None,
                source_type=COMPASS_EVENT_SOURCE_TYPE,
                source_id=f"run-{tenant_id}",
                message="seed",
                payload_json=payload,
            )
        )
        s.commit()


def _compass_tasks_for(tenant_id: str) -> list[GovernanceWorkflowTaskTable]:
    with Session(engine) as s:
        return list(
            s.scalars(
                select(GovernanceWorkflowTaskTable).where(
                    GovernanceWorkflowTaskTable.tenant_id == tenant_id,
                    GovernanceWorkflowTaskTable.source_type == COMPASS_EVENT_SOURCE_TYPE,
                )
            )
        )


def test_low_confidence_event_creates_compass_task() -> None:
    tenant = "compass-rule-low-conf"
    _seed_compass_event(
        tenant_id=tenant,
        event_type=COMPASS_EVENT_TYPE_COMPLETED,
        confidence=COMPASS_TASK_CONFIDENCE_FLOOR - 5,
    )
    r = client.post(
        "/api/v1/governance/workflows/run",
        headers=_h(tenant),
        json={"rule_profile": "default"},
    )
    assert r.status_code == 201, r.text
    tasks = _compass_tasks_for(tenant)
    assert len(tasks) == 1
    t = tasks[0]
    assert "Compass-Confidence kritisch" in t.title
    assert t.template_code == "tpl_compass_data_quality"
    assert "EU_AI_ACT" in (t.framework_tags_json or [])


def test_failed_event_creates_compass_task_marked_high_priority() -> None:
    tenant = "compass-rule-failed"
    _seed_compass_event(
        tenant_id=tenant,
        event_type=COMPASS_EVENT_TYPE_FAILED,
        confidence=None,
        error_type="OperationalError",
    )
    r = client.post(
        "/api/v1/governance/workflows/run",
        headers=_h(tenant),
        json={"rule_profile": "default"},
    )
    assert r.status_code == 201, r.text
    tasks = _compass_tasks_for(tenant)
    assert len(tasks) == 1
    assert tasks[0].priority == "high"


def test_healthy_event_does_not_create_task() -> None:
    """Erfolgreicher Run mit hoher Confidence → kein Task (kein Flood)."""
    tenant = "compass-rule-healthy"
    _seed_compass_event(
        tenant_id=tenant,
        event_type=COMPASS_EVENT_TYPE_COMPLETED,
        confidence=85,
    )
    r = client.post(
        "/api/v1/governance/workflows/run",
        headers=_h(tenant),
        json={"rule_profile": "default"},
    )
    assert r.status_code == 201, r.text
    tasks = _compass_tasks_for(tenant)
    assert tasks == []


def test_compass_task_is_idempotent_within_same_day() -> None:
    """Zwei Sync-Runs am selben Tag erzeugen dedupe-bedingt nur einen Task."""
    tenant = "compass-rule-dedupe"
    _seed_compass_event(
        tenant_id=tenant,
        event_type=COMPASS_EVENT_TYPE_FAILED,
        confidence=None,
        error_type="OperationalError",
    )
    h = _h(tenant)
    r1 = client.post(
        "/api/v1/governance/workflows/run", headers=h, json={"rule_profile": "default"}
    )
    r2 = client.post(
        "/api/v1/governance/workflows/run", headers=h, json={"rule_profile": "default"}
    )
    assert r1.status_code == 201 and r2.status_code == 201
    assert len(_compass_tasks_for(tenant)) == 1


def test_only_latest_event_drives_rule_decision() -> None:
    """Letzter Event ist healthy → kein Task, auch wenn früher ein failed-Event lag."""
    tenant = "compass-rule-recovery"
    older = datetime.now(UTC) - timedelta(hours=2)
    newer = datetime.now(UTC)
    _seed_compass_event(
        tenant_id=tenant,
        event_type=COMPASS_EVENT_TYPE_FAILED,
        confidence=None,
        error_type="OperationalError",
        at=older,
    )
    _seed_compass_event(
        tenant_id=tenant,
        event_type=COMPASS_EVENT_TYPE_COMPLETED,
        confidence=80,
        at=newer,
    )
    r = client.post(
        "/api/v1/governance/workflows/run",
        headers=_h(tenant),
        json={"rule_profile": "default"},
    )
    assert r.status_code == 201, r.text
    assert _compass_tasks_for(tenant) == []
