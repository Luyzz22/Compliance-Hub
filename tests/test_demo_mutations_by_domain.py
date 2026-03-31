"""Demo read-only: repräsentative Mutations-Endpunkte (KPIs, Board-Report)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DEMO_KEY = "demo-seed-key"
T_KPI = "demo-domain-kpi-tenant"
T_BR = "demo-domain-br-tenant"


def _demo_headers() -> dict[str, str]:
    return {"x-api-key": DEMO_KEY}


def _tenant_headers(tid: str) -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-tenant-id": tid}


def test_post_ai_kpi_blocked_after_demo_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_KPI_KRI", "true")
    r = client.post(
        "/api/v1/demo/tenants/seed",
        headers=_demo_headers(),
        json={"template_key": "tax_advisor", "tenant_id": T_KPI},
    )
    assert r.status_code == 200, r.text
    systems = client.get("/api/v1/ai-systems", headers=_tenant_headers(T_KPI)).json()
    assert len(systems) >= 1
    sid = systems[0]["id"]

    r_list = client.get(
        f"/api/v1/tenants/{T_KPI}/ai-systems/{sid}/kpis",
        headers=_tenant_headers(T_KPI),
    )
    assert r_list.status_code == 200, r_list.text
    def_id = r_list.json()["series"][0]["definition"]["id"]
    p0 = datetime(2025, 1, 1, tzinfo=UTC)
    p1 = datetime(2025, 3, 31, tzinfo=UTC)

    r2 = client.post(
        f"/api/v1/tenants/{T_KPI}/ai-systems/{sid}/kpis",
        headers=_tenant_headers(T_KPI),
        json={
            "kpi_definition_id": def_id,
            "period_start": p0.isoformat(),
            "period_end": p1.isoformat(),
            "value": 1.0,
        },
    )
    assert r2.status_code == 403
    d = r2.json()["detail"]
    if isinstance(d, dict):
        assert d.get("code") == "demo_tenant_readonly"


def test_post_board_report_blocked_after_demo_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT", "true")
    r = client.post(
        "/api/v1/demo/tenants/seed",
        headers=_demo_headers(),
        json={"template_key": "industrial_sme", "tenant_id": T_BR},
    )
    assert r.status_code == 200, r.text

    r2 = client.post(
        f"/api/v1/tenants/{T_BR}/board/ai-compliance-report",
        headers=_tenant_headers(T_BR),
        json={
            "audience_type": "board",
            "focus_frameworks": None,
            "include_ai_act_only": False,
            "language": "de",
        },
    )
    assert r2.status_code == 403
    d = r2.json()["detail"]
    if isinstance(d, dict):
        assert d.get("code") == "demo_tenant_readonly"
