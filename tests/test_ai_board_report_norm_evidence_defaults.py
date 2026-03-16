"""Tests für NormEvidence-Default-Vorschläge Endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import _headers

client = TestClient(app)


def test_norm_evidence_defaults_returns_non_empty_list() -> None:
    resp = client.get(
        "/api/v1/ai-governance/report/board/norm-evidence-defaults",
        headers=_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_norm_evidence_defaults_values_valid() -> None:
    resp = client.get(
        "/api/v1/ai-governance/report/board/norm-evidence-defaults",
        headers=_headers(),
    )
    assert resp.status_code == 200
    items = resp.json()
    allowed_frameworks = {"EU_AI_ACT", "NIS2", "ISO_42001"}
    allowed_evidence_types = {"board_report", "export_job", "other"}
    for it in items:
        assert it["framework"] in allowed_frameworks
        assert it["evidence_type"] in allowed_evidence_types
        assert isinstance(it["reference"], str) and it["reference"].strip()


def test_norm_evidence_defaults_401_no_api_key() -> None:
    resp = client.get(
        "/api/v1/ai-governance/report/board/norm-evidence-defaults",
        headers={"x-tenant-id": "board-kpi-tenant"},
    )
    assert resp.status_code == 401
