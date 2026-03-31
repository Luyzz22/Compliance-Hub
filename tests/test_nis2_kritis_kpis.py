"""Tests für NIS2-/KRITIS-KPI-Endpunkte und Tenant-Isolation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.ai_system_models import (
    AIActCategory,
    AISystemCriticality,
    AISystemRiskLevel,
    DataSensitivity,
)
from app.main import app

client = TestClient(app)


def _headers(tenant_id: str = "tenant-nis2-kpi-001") -> dict[str, str]:
    return {
        "x-api-key": "test-api-key",
        "x-tenant-id": tenant_id,
    }


def _create_ai_system(system_id: str, tenant_headers: dict[str, str]) -> None:
    payload = {
        "id": system_id,
        "name": "NIS2 KPI Test System",
        "description": "Produktion Qualität",
        "business_unit": "Fertigung Süd",
        "risk_level": AISystemRiskLevel.high.value,
        "ai_act_category": AIActCategory.high_risk.value,
        "gdpr_dpia_required": True,
        "owner_email": "owner@example.com",
        "criticality": AISystemCriticality.high.value,
        "data_sensitivity": DataSensitivity.internal.value,
        "has_incident_runbook": True,
        "has_supplier_risk_register": True,
        "has_backup_runbook": True,
    }
    r = client.post("/api/v1/ai-systems", json=payload, headers=tenant_headers)
    assert r.status_code == 200, r.text


def test_nis2_kpis_get_and_upsert() -> None:
    h = _headers()
    _create_ai_system("nis2-ai-1", h)

    get_empty = client.get(
        "/api/v1/ai-systems/nis2-ai-1/nis2-kritis-kpis",
        headers=h,
    )
    assert get_empty.status_code == 200
    body = get_empty.json()
    assert body["kpis"] == []
    assert body["recommended"] is not None
    assert body["recommended"]["scenario_profile_id"] == "manufacturing_quality_control"

    post = client.post(
        "/api/v1/ai-systems/nis2-ai-1/nis2-kritis-kpis",
        headers=h,
        json={
            "kpi_type": "INCIDENT_RESPONSE_MATURITY",
            "value_percent": 77,
            "evidence_ref": '{"norm_evidence_ids":["ev-1"]}',
        },
    )
    assert post.status_code == 200
    saved = post.json()
    assert saved["kpi_type"] == "INCIDENT_RESPONSE_MATURITY"
    assert saved["value_percent"] == 77

    get_one = client.get(
        "/api/v1/ai-systems/nis2-ai-1/nis2-kritis-kpis",
        headers=h,
    )
    assert get_one.status_code == 200
    assert len(get_one.json()["kpis"]) == 1


def test_nis2_kpis_404_foreign_system() -> None:
    h = _headers("tenant-nis2-kpi-a")
    _create_ai_system("nis2-ai-a", h)

    other = _headers("tenant-nis2-kpi-b")
    r = client.get(
        "/api/v1/ai-systems/nis2-ai-a/nis2-kritis-kpis",
        headers=other,
    )
    assert r.status_code == 404


def test_ai_governance_kpis_includes_nis2_aggregate() -> None:
    h = _headers("tenant-nis2-agg-only")
    _create_ai_system("nis2-ai-agg", h)
    client.post(
        "/api/v1/ai-systems/nis2-ai-agg/nis2-kritis-kpis",
        headers=h,
        json={"kpi_type": "OT_IT_SEGREGATION", "value_percent": 50},
    )

    r = client.get(
        "/api/v1/tenants/tenant-nis2-agg-only/ai-governance-kpis",
        headers=h,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["nis2_kritis_kpi_mean_percent"] == 50.0
    assert "nis2_kritis_systems_full_coverage_ratio" in data
