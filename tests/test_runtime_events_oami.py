"""Runtime-Event-Ingest und OAMI-APIs (Mandantenisolation, Idempotenz)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.ai_system_models import (
    AIActCategory,
    AISystemCriticality,
    AISystemRiskLevel,
    DataSensitivity,
)
from app.db import SessionLocal
from app.main import app
from app.models_db import AiRuntimeEventTable
from app.services.operational_monitoring_index import compute_tenant_operational_monitoring_index


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _headers(tenant_id: str) -> dict[str, str]:
    return {"x-api-key": "test-api-key", "x-tenant-id": tenant_id}


def _create_system(client: TestClient, tenant_id: str, system_id: str) -> None:
    payload = {
        "id": system_id,
        "name": "OAMI Test System",
        "description": "Test",
        "business_unit": "BU",
        "risk_level": AISystemRiskLevel.high.value,
        "ai_act_category": AIActCategory.high_risk.value,
        "gdpr_dpia_required": True,
        "criticality": AISystemCriticality.high.value,
        "data_sensitivity": DataSensitivity.internal.value,
        "has_incident_runbook": True,
        "has_supplier_risk_register": True,
        "has_backup_runbook": True,
    }
    r = client.post("/api/v1/ai-systems", json=payload, headers=_headers(tenant_id))
    assert r.status_code == 200, r.text


def test_runtime_events_ingest_idempotent_and_oami_apis(client: TestClient) -> None:
    tid = f"oami-{uuid.uuid4().hex[:12]}"
    h = _headers(tid)
    sid = "oami-sys-1"
    _create_system(client, tid, sid)

    now = datetime.now(UTC)
    batch = {
        "events": [
            {
                "source_event_id": "ev-heartbeat-1",
                "source": "sap_ai_core",
                "event_type": "heartbeat",
                "occurred_at": now.isoformat(),
                "extra": {"unknown": "drop-me", "region": "eu-de"},
            },
        ],
    }
    r1 = client.post(f"/api/v1/ai-systems/{sid}/runtime-events", json=batch, headers=h)
    assert r1.status_code == 200, r1.text
    assert r1.json() == {"inserted": 1, "skipped_duplicate": 0, "kpi_updates": 0}

    r1b = client.post(f"/api/v1/ai-systems/{sid}/runtime-events", json=batch, headers=h)
    assert r1b.status_code == 200
    assert r1b.json()["skipped_duplicate"] == 1

    with SessionLocal() as s:
        stmt = select(AiRuntimeEventTable).where(
            AiRuntimeEventTable.tenant_id == tid,
            AiRuntimeEventTable.source_event_id == "ev-heartbeat-1",
        )
        ev_row = s.execute(stmt).scalar_one()
        assert ev_row.extra == {"region": "eu-de"}

    r_idx = client.get(f"/api/v1/ai-systems/{sid}/monitoring-index", headers=h)
    assert r_idx.status_code == 200
    body = r_idx.json()
    assert body["ai_system_id"] == sid
    assert body["tenant_id"] == tid
    assert body["has_data"] is True
    assert 0 <= body["operational_monitoring_index"] <= 100
    assert body["level"] in ("low", "medium", "high")
    assert "freshness" in body["components"]

    r_t = client.get(f"/api/v1/tenants/{tid}/operational-monitoring-index", headers=h)
    assert r_t.status_code == 200
    t_body = r_t.json()
    assert t_body["tenant_id"] == tid
    assert t_body["systems_scored"] >= 1
    assert t_body["has_any_runtime_data"] is True


def test_runtime_events_404_when_system_not_in_tenant(client: TestClient) -> None:
    tid = f"oami-{uuid.uuid4().hex[:12]}"
    h = _headers(tid)
    batch = {
        "events": [
            {
                "source_event_id": "x",
                "source": "sap_ai_core",
                "event_type": "heartbeat",
                "occurred_at": datetime.now(UTC).isoformat(),
            },
        ],
    }
    r = client.post("/api/v1/ai-systems/missing-sys/runtime-events", json=batch, headers=h)
    assert r.status_code == 404


def test_tenant_prefixed_runtime_events_and_monitoring_alias(client: TestClient) -> None:
    tid = f"oami-{uuid.uuid4().hex[:12]}"
    h = _headers(tid)
    sid = "oami-alias-sys"
    _create_system(client, tid, sid)
    now = datetime.now(UTC)
    batch = {
        "events": [
            {
                "source_event_id": "alias-ev-1",
                "source": "sap_ai_core",
                "event_type": "heartbeat",
                "occurred_at": now.isoformat(),
            },
        ],
    }
    r_post = client.post(
        f"/api/v1/tenants/{tid}/ai-systems/{sid}/runtime-events",
        json=batch,
        headers=h,
    )
    assert r_post.status_code == 200, r_post.text
    assert r_post.json()["inserted"] == 1

    r_get = client.get(
        f"/api/v1/tenants/{tid}/ai-systems/{sid}/monitoring-index",
        headers=h,
    )
    assert r_get.status_code == 200
    assert r_get.json()["ai_system_id"] == sid
    assert r_get.json()["tenant_id"] == tid


def test_tenant_operational_monitoring_index_tenant_mismatch(client: TestClient) -> None:
    tid = f"oami-{uuid.uuid4().hex[:12]}"
    h = _headers(tid)
    r = client.get("/api/v1/tenants/other-tenant/operational-monitoring-index", headers=h)
    assert r.status_code == 403


def test_tenant_prefixed_monitoring_index_path_tenant_mismatch(client: TestClient) -> None:
    tid = f"oami-{uuid.uuid4().hex[:12]}"
    h = _headers(tid)
    r = client.get(
        "/api/v1/tenants/wrong-tenant/ai-systems/any-sys/monitoring-index",
        headers=h,
    )
    assert r.status_code == 403


def test_compute_tenant_persist_snapshot_writes_row(client: TestClient) -> None:
    tid = f"oami-{uuid.uuid4().hex[:12]}"
    h = _headers(tid)
    sid = "oami-sys-snap"
    _create_system(client, tid, sid)
    now = datetime.now(UTC)
    client.post(
        f"/api/v1/ai-systems/{sid}/runtime-events",
        headers=h,
        json={
            "events": [
                {
                    "source_event_id": "snap-1",
                    "source": "manual_import",
                    "event_type": "metric_snapshot",
                    "occurred_at": now.isoformat(),
                    "metric_key": "nonexistent_kpi",
                    "value": 1.0,
                },
            ],
        },
    )
    from app.models_db import TenantOperationalMonitoringSnapshotTable

    with SessionLocal() as s:
        out = compute_tenant_operational_monitoring_index(
            s,
            tid,
            window_days=90,
            persist_snapshot=True,
        )
        assert out.has_any_runtime_data is True
        expected_idx = out.operational_monitoring_index

    with SessionLocal() as s2:
        snap = s2.get(TenantOperationalMonitoringSnapshotTable, (tid, 90))
        assert snap is not None
        assert snap.index_value == expected_idx


def test_incidents_lower_oami(client: TestClient) -> None:
    tid = f"oami-{uuid.uuid4().hex[:12]}"
    h = _headers(tid)
    sid = "oami-sys-inc"
    _create_system(client, tid, sid)
    now = datetime.now(UTC)
    events = []
    for i in range(5):
        events.append(
            {
                "source_event_id": f"inc-{i}",
                "source": "sap_ai_core",
                "event_type": "incident",
                "severity": "high",
                "occurred_at": (now - timedelta(hours=i)).isoformat(),
            },
        )
    r = client.post(
        f"/api/v1/ai-systems/{sid}/runtime-events",
        headers=h,
        json={"events": events},
    )
    assert r.status_code == 200
    quiet_tid = f"oami-{uuid.uuid4().hex[:12]}"
    quiet_h = _headers(quiet_tid)
    _create_system(client, quiet_tid, "quiet-sys")
    client.post(
        "/api/v1/ai-systems/quiet-sys/runtime-events",
        headers=quiet_h,
        json={
            "events": [
                {
                    "source_event_id": "q1",
                    "source": "sap_ai_core",
                    "event_type": "heartbeat",
                    "occurred_at": now.isoformat(),
                },
            ],
        },
    )
    noisy = client.get(f"/api/v1/ai-systems/{sid}/monitoring-index", headers=h).json()[
        "operational_monitoring_index"
    ]
    quiet = client.get(
        "/api/v1/ai-systems/quiet-sys/monitoring-index",
        headers=quiet_h,
    ).json()["operational_monitoring_index"]
    assert noisy < quiet
