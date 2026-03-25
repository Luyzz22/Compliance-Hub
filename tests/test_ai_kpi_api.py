"""API-Tests: AI-KPI/KRI (Tenant-Pfade, Feature-Flag, Summary)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.ai_system_models import (
    AIActCategory,
    AISystemCriticality,
    AISystemRiskLevel,
    DataSensitivity,
)
from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _headers(tenant_id: str) -> dict[str, str]:
    return {"x-api-key": "test-api-key", "x-tenant-id": tenant_id}


def _create_high_risk_system(
    client: TestClient,
    system_id: str,
    tenant_headers: dict[str, str],
) -> None:
    payload = {
        "id": system_id,
        "name": "KPI Test HR System",
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
    r = client.post("/api/v1/ai-systems", json=payload, headers=tenant_headers)
    assert r.status_code == 200, r.text


def test_ai_kpi_get_list_and_upsert(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_KPI_KRI", "true")
    tid = f"kpi-api-{uuid.uuid4().hex[:12]}"
    h = _headers(tid)
    sid = "kpi-sys-1"
    _create_high_risk_system(client, sid, h)

    r_list = client.get(
        f"/api/v1/tenants/{tid}/ai-systems/{sid}/kpis",
        headers=h,
    )
    assert r_list.status_code == 200
    body = r_list.json()
    assert body["ai_system_id"] == sid
    assert len(body["series"]) >= 8
    def_id = body["series"][0]["definition"]["id"]

    p0 = datetime(2025, 1, 1, tzinfo=UTC)
    p1 = datetime(2025, 3, 31, tzinfo=UTC)
    r_post = client.post(
        f"/api/v1/tenants/{tid}/ai-systems/{sid}/kpis",
        headers=h,
        json={
            "kpi_definition_id": def_id,
            "period_start": p0.isoformat(),
            "period_end": p1.isoformat(),
            "value": 4.2,
            "source": "manual",
            "comment": "Q1",
        },
    )
    assert r_post.status_code == 200, r_post.text
    assert r_post.json()["value"] == 4.2

    r_list2 = client.get(
        f"/api/v1/tenants/{tid}/ai-systems/{sid}/kpis",
        headers=h,
    )
    assert r_list2.status_code == 200
    match = next(
        (s for s in r_list2.json()["series"] if s["definition"]["id"] == def_id),
        None,
    )
    assert match is not None
    assert len(match["periods"]) == 1


def test_ai_kpi_summary_aggregate(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_KPI_KRI", "true")
    tid = f"kpi-sum-{uuid.uuid4().hex[:12]}"
    h = _headers(tid)
    sid = "kpi-sys-sum"
    _create_high_risk_system(client, sid, h)

    r0 = client.get(f"/api/v1/tenants/{tid}/ai-systems/{sid}/kpis", headers=h)
    def_id = r0.json()["series"][0]["definition"]["id"]

    client.post(
        f"/api/v1/tenants/{tid}/ai-systems/{sid}/kpis",
        headers=h,
        json={
            "kpi_definition_id": def_id,
            "period_start": datetime(2024, 10, 1, tzinfo=UTC).isoformat(),
            "period_end": datetime(2024, 12, 31, tzinfo=UTC).isoformat(),
            "value": 1.0,
            "source": "manual",
        },
    )
    client.post(
        f"/api/v1/tenants/{tid}/ai-systems/{sid}/kpis",
        headers=h,
        json={
            "kpi_definition_id": def_id,
            "period_start": datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
            "period_end": datetime(2025, 3, 31, tzinfo=UTC).isoformat(),
            "value": 3.0,
            "source": "manual",
        },
    )

    r_sum = client.get(
        f"/api/v1/tenants/{tid}/ai-kpis/summary",
        headers=h,
    )
    assert r_sum.status_code == 200
    data = r_sum.json()
    assert data["high_risk_system_count"] >= 1
    keys = {x["kpi_key"] for x in data["per_kpi"]}
    assert keys  # seeded definitions present


def test_ai_kpi_forbidden_when_feature_off(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_KPI_KRI", "false")
    tid = "kpi-off"
    h = _headers(tid)
    r = client.get(f"/api/v1/tenants/{tid}/ai-systems/x/kpis", headers=h)
    assert r.status_code == 403


def test_ai_kpi_path_tenant_mismatch(client: TestClient) -> None:
    tid = "kpi-path-a"
    h = _headers("kpi-path-b")
    r = client.get(f"/api/v1/tenants/{tid}/ai-systems/x/kpis", headers=h)
    assert r.status_code == 403
