"""Tests für GET /api/v1/ai-governance/high-risk-scenarios."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import _headers

client = TestClient(app)

_ALLOWED_FRAMEWORKS = {"EU_AI_ACT", "NIS2", "ISO_42001"}
_ALLOWED_EVIDENCE_TYPES = {"board_report", "export_job", "other"}


def test_high_risk_scenarios_includes_core_profiles() -> None:
    resp = client.get(
        "/api/v1/ai-governance/high-risk-scenarios",
        headers=_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    ids = {p["id"] for p in data}
    assert "manufacturing_quality_control" in ids
    assert "critical_infrastructure_predictive_maintenance" in ids
    by_id = {p["id"]: p for p in data}
    assert (
        by_id["manufacturing_quality_control"]["label"]
        == "Qualitätskontrolle (High-Risk AI im produzierenden Gewerbe)"
    )
    assert (
        by_id["critical_infrastructure_predictive_maintenance"]["label"]
        == "Predictive Maintenance (kritische Infrastruktur)"
    )
    assert "clinical_decision_support" in ids
    assert "biometric_identification_high_risk" in ids
    assert "hr_recruitment_screening" in ids
    mfg = by_id["manufacturing_quality_control"]
    assert mfg.get("recommended_incident_response_maturity_percent") == 88


def test_high_risk_scenarios_recommended_evidence_valid() -> None:
    resp = client.get(
        "/api/v1/ai-governance/high-risk-scenarios",
        headers=_headers(),
    )
    assert resp.status_code == 200
    for profile in resp.json():
        for ev in profile["recommended_evidence"]:
            assert ev["framework"] in _ALLOWED_FRAMEWORKS
            assert ev["evidence_type"] in _ALLOWED_EVIDENCE_TYPES
            assert isinstance(ev["reference"], str) and ev["reference"].strip()


def test_high_risk_scenarios_401_no_api_key() -> None:
    resp = client.get(
        "/api/v1/ai-governance/high-risk-scenarios",
        headers={"x-tenant-id": "board-kpi-tenant"},
    )
    assert resp.status_code == 401
