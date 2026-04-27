"""Compliance Compass — Run-Observability + Governance-Andocken.

Decken ab:
- Erfolgreicher Run schreibt einen ``compass.run.completed``-Event.
- DB-Fehler in der Pipeline schreibt zusätzlich ``compass.run.failed`` (mit error_type)
  und liefert :class:`ComplianceCompassError` an den Aufrufer.
- ``get_latest_compass_signal`` liefert deterministische Werte aus dem letzten Event
  (Quelle: ``governance_workflow_events``), inkl. ``unknown`` für Tenants ohne Run.
- Audit-Readiness-API liefert das ``compass_signal``-Feld erwartungsgemäß.
- Board-Reporting nimmt den letzten Compass-Run als KPI auf.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app
from app.models_db import GovernanceWorkflowEventTable
from app.services.compliance_compass_service import (
    COMPASS_EVENT_SOURCE_TYPE,
    COMPASS_EVENT_TYPE_COMPLETED,
    COMPASS_EVENT_TYPE_FAILED,
    LOW_CONFIDENCE_THRESHOLD,
    ComplianceCompassError,
    build_compass_snapshot,
    get_latest_compass_signal,
)

client = TestClient(app)


def _h(tid: str) -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-tenant-id": tid}


def _events_for(tenant_id: str) -> list[GovernanceWorkflowEventTable]:
    with Session(engine) as s:
        rows = s.scalars(
            select(GovernanceWorkflowEventTable)
            .where(
                GovernanceWorkflowEventTable.tenant_id == tenant_id,
                GovernanceWorkflowEventTable.source_type == COMPASS_EVENT_SOURCE_TYPE,
            )
            .order_by(GovernanceWorkflowEventTable.at_utc.desc())
        ).all()
        # Detach so callers can read attributes after the session closes.
        return [s.merge(r, load=False) for r in rows]


# --------------------------------------------------------------------------------------
# Successful run → completed event with audit-relevant payload (no PII).
# --------------------------------------------------------------------------------------


def test_successful_compass_run_writes_completed_event_with_payload() -> None:
    tenant = "compass-obs-tenant-success"
    r = client.get("/api/v1/governance/compass/snapshot", headers=_h(tenant))
    assert r.status_code == 200, r.text
    body = r.json()

    events = _events_for(tenant)
    completed = [e for e in events if e.event_type == COMPASS_EVENT_TYPE_COMPLETED]
    assert len(completed) >= 1, "expected at least one compass.run.completed event"
    payload = completed[0].payload_json or {}
    assert payload.get("fusion_index_0_100") == body["fusion_index_0_100"]
    assert payload.get("confidence_0_100") == body["confidence_0_100"]
    assert payload.get("posture") == body["posture"]
    assert payload.get("model_version") == body["model_version"]
    # Defensive: kein offensichtlicher PII-Leak in Payload-Keys.
    forbidden = {"email", "user_email", "name", "ip_address"}
    assert forbidden.isdisjoint(set(payload.keys()))


# --------------------------------------------------------------------------------------
# DB failure → failed event + ComplianceCompassError, no PendingRollbackError after.
# --------------------------------------------------------------------------------------


def test_db_failure_writes_failed_event_and_raises_compass_error() -> None:
    """Hinter ``_strategic_signal`` (welches Readiness-Failures bereits dämpft) bricht
    eine harte DB-Exception aus dem Workflow-Score-Pfad — der Service muss rollbacken,
    einen ``compass.run.failed``-Event schreiben und ``ComplianceCompassError`` werfen.
    """
    tenant = "compass-obs-tenant-failure"

    def _boom(*_args, **_kwargs):
        raise OperationalError("SELECT count(*)", {}, Exception("boom"))

    with Session(engine) as s, patch(
        "app.services.compliance_compass_service._count_tasks",
        side_effect=_boom,
    ):
        try:
            build_compass_snapshot(s, tenant)
        except ComplianceCompassError:
            pass
        else:  # pragma: no cover - unerwartet
            raise AssertionError("expected ComplianceCompassError")

    events = _events_for(tenant)
    failed = [e for e in events if e.event_type == COMPASS_EVENT_TYPE_FAILED]
    assert len(failed) == 1
    payload = failed[0].payload_json or {}
    assert payload.get("error_type") == "OperationalError"
    assert payload.get("stage") == "snapshot_pipeline"
    assert failed[0].severity == "error"


# --------------------------------------------------------------------------------------
# get_latest_compass_signal: deterministische Ergebnisse für Audit/Board/Workflow.
# --------------------------------------------------------------------------------------


def test_latest_compass_signal_unknown_for_pristine_tenant() -> None:
    with Session(engine) as s:
        sig = get_latest_compass_signal(s, "compass-obs-pristine-tenant")
    assert sig.result == "unknown"
    assert sig.latest_run_at is None
    assert sig.confidence_0_100 is None


def test_latest_compass_signal_returns_warning_when_low_confidence() -> None:
    tenant = "compass-obs-low-conf"
    now = datetime.now(UTC)
    with Session(engine) as s:
        s.add(
            GovernanceWorkflowEventTable(
                id="evt-low-1",
                tenant_id=tenant,
                at_utc=now - timedelta(minutes=5),
                event_type=COMPASS_EVENT_TYPE_COMPLETED,
                severity="info",
                ref_task_id=None,
                source_type=COMPASS_EVENT_SOURCE_TYPE,
                source_id="run-low-1",
                message="seed",
                payload_json={
                    "fusion_index_0_100": 30,
                    "confidence_0_100": LOW_CONFIDENCE_THRESHOLD - 5,
                    "posture": "elevated",
                    "model_version": "test",
                    "readiness_level": "basic",
                },
            )
        )
        s.commit()
        sig = get_latest_compass_signal(s, tenant)
    assert sig.result == "warning"
    assert sig.confidence_0_100 == LOW_CONFIDENCE_THRESHOLD - 5
    assert sig.posture == "elevated"


def test_latest_compass_signal_returns_error_for_failed_run() -> None:
    tenant = "compass-obs-failed-state"
    now = datetime.now(UTC)
    with Session(engine) as s:
        s.add(
            GovernanceWorkflowEventTable(
                id="evt-fail-1",
                tenant_id=tenant,
                at_utc=now,
                event_type=COMPASS_EVENT_TYPE_FAILED,
                severity="error",
                ref_task_id=None,
                source_type=COMPASS_EVENT_SOURCE_TYPE,
                source_id="run-fail-1",
                message="failure",
                payload_json={
                    "error_type": "OperationalError",
                    "stage": "snapshot_pipeline",
                    "model_version": "test",
                },
            )
        )
        s.commit()
        sig = get_latest_compass_signal(s, tenant)
    assert sig.result == "error"
    assert sig.error_type == "OperationalError"
    assert sig.confidence_0_100 is None


# --------------------------------------------------------------------------------------
# Audit-Readiness-API liefert compass_signal mit.
# --------------------------------------------------------------------------------------


def test_audit_readiness_summary_exposes_compass_signal() -> None:
    h = _h("compass-obs-audit-tenant")
    # Trigger einen Compass-Run, damit ein Event existiert.
    snap = client.get("/api/v1/governance/compass/snapshot", headers=h)
    assert snap.status_code == 200, snap.text

    # Minimaler Audit-Case (kein Control nötig — compass_signal stammt aus events).
    a = client.post(
        "/api/v1/governance/audits",
        headers=h,
        json={
            "title": "Compass-aware audit",
            "framework_tags": ["EU_AI_ACT"],
            "control_ids": [],
        },
    )
    assert a.status_code == 201, a.text
    aid = a.json()["id"]
    r = client.get(f"/api/v1/governance/audits/{aid}/readiness", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "compass_signal" in body
    cs = body["compass_signal"]
    assert cs["result"] in ("ok", "warning")  # Run war erfolgreich
    assert cs["confidence_0_100"] == snap.json()["confidence_0_100"]
    assert cs["latest_run_at"] is not None


# --------------------------------------------------------------------------------------
# Board-Reporting: Compass-Box in Metrics.
# --------------------------------------------------------------------------------------


def test_board_report_metrics_include_compass_box() -> None:
    h = _h("compass-obs-board-tenant")
    snap = client.get("/api/v1/governance/compass/snapshot", headers=h)
    assert snap.status_code == 200, snap.text
    confidence = snap.json()["confidence_0_100"]

    period_start = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    period_end = datetime.now(UTC).isoformat()
    g = client.post(
        "/api/v1/governance/board-reports/generate",
        headers=h,
        json={
            "period_key": "2026-04",
            "period_type": "monthly",
            "period_start": period_start,
            "period_end": period_end,
            "title": "Compass Observability Test Pack",
        },
    )
    assert g.status_code == 201, g.text
    metrics = {m["metric_key"]: m for m in g.json()["summary"]["metrics"]}
    assert "compass_confidence_0_100" in metrics
    assert "compass_fusion_0_100" in metrics
    assert metrics["compass_confidence_0_100"]["value"] == float(confidence)
    assert metrics["compass_confidence_0_100"]["traffic_light"] in ("green", "amber", "red")
