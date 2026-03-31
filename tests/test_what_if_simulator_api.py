"""Board-What-if-Simulator API."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import _headers

client = TestClient(app)


def test_what_if_forbidden_when_feature_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_WHAT_IF_SIMULATOR", "false")
    r = client.post(
        "/api/v1/ai-governance/what-if/board-impact",
        headers=_headers(),
        json={"kpi_adjustments": []},
    )
    assert r.status_code == 403


def test_what_if_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_WHAT_IF_SIMULATOR", "true")
    tid = f"wf-tenant-{uuid.uuid4().hex[:10]}"
    h = {"x-api-key": "board-kpi-key", "x-tenant-id": tid}
    wf_sys = f"wf-sys-{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": wf_sys,
            "name": "What-If System",
            "description": "Test",
            "business_unit": "Ops",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "owner_email": "o@x.de",
            "criticality": "high",
            "data_sensitivity": "internal",
            "has_incident_runbook": True,
            "has_supplier_risk_register": True,
            "has_backup_runbook": True,
        },
        headers=h,
    )
    for kt, val in (
        ("INCIDENT_RESPONSE_MATURITY", 20),
        ("SUPPLIER_RISK_COVERAGE", 20),
        ("OT_IT_SEGREGATION", 20),
    ):
        client.post(
            f"/api/v1/ai-systems/{wf_sys}/nis2-kritis-kpis",
            headers=h,
            json={"kpi_type": kt, "value_percent": val},
        )

    r0 = client.post(
        "/api/v1/ai-governance/what-if/board-impact",
        headers=h,
        json={"kpi_adjustments": []},
    )
    assert r0.status_code == 200
    base = r0.json()
    assert 0.0 <= base["original_readiness"] <= 1.0
    assert base["simulated_readiness"] == base["original_readiness"]

    r1 = client.post(
        "/api/v1/ai-governance/what-if/board-impact",
        headers=h,
        json={
            "kpi_adjustments": [
                {
                    "ai_system_id": wf_sys,
                    "kpi_type": "INCIDENT_RESPONSE_MATURITY",
                    "target_value_percent": 95,
                },
                {
                    "ai_system_id": wf_sys,
                    "kpi_type": "SUPPLIER_RISK_COVERAGE",
                    "target_value_percent": 95,
                },
                {
                    "ai_system_id": wf_sys,
                    "kpi_type": "OT_IT_SEGREGATION",
                    "target_value_percent": 95,
                },
            ],
        },
    )
    assert r1.status_code == 200
    sim = r1.json()
    assert sim["simulated_board_kpis"]["nis2_kritis_kpi_mean_percent"] == 95.0
    assert sim["simulated_readiness"] >= base["original_readiness"]


def test_what_if_orphan_system_adjustment_no_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_WHAT_IF_SIMULATOR", "true")
    tid = f"wf-orphan-{uuid.uuid4().hex[:10]}"
    h = {"x-api-key": "board-kpi-key", "x-tenant-id": tid}
    r = client.post(
        "/api/v1/ai-governance/what-if/board-impact",
        headers=h,
        json={
            "kpi_adjustments": [
                {
                    "ai_system_id": "does-not-exist",
                    "kpi_type": "INCIDENT_RESPONSE_MATURITY",
                    "target_value_percent": 99,
                },
            ],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["original_readiness"] == data["simulated_readiness"]
