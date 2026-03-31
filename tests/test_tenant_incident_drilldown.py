"""Incident-Drilldown: Aggregation und API (Mandant / Advisor)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.services.tenant_incident_drilldown import (
    compute_tenant_incident_drilldown,
    event_source_supplier_label_de,
    tenant_incident_drilldown_to_csv,
)

client = TestClient(app)

ADV_DR = "advisor-drill@example.com"
API_KEY = "board-kpi-key"
T_DRILL = "drill-tenant-a"
T_OTHER = "drill-tenant-b"


@pytest.fixture
def advisor_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ADVISOR_IDS", ADV_DR)


def _adv_headers() -> dict[str, str]:
    return {"x-api-key": API_KEY, "x-advisor-id": ADV_DR}


def _seed_advisor_link() -> None:
    s = SessionLocal()
    try:
        AdvisorTenantRepository(s).upsert_link(
            advisor_id=ADV_DR,
            tenant_id=T_DRILL,
            tenant_display_name="Drill GmbH",
            industry="IT",
            country="DE",
        )
    finally:
        s.close()


def _create_system(tenant_id: str, system_id: str, name: str) -> None:
    r = client.post(
        "/api/v1/ai-systems",
        json={
            "id": system_id,
            "name": name,
            "description": "d",
            "business_unit": "BU",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": False,
            "owner_email": "",
            "criticality": "medium",
            "data_sensitivity": "internal",
            "has_incident_runbook": False,
            "has_supplier_risk_register": False,
            "has_backup_runbook": False,
        },
        headers={"x-api-key": API_KEY, "x-tenant-id": tenant_id},
    )
    assert r.status_code == 200, r.text


def _ingest_incidents(
    tenant_id: str,
    system_id: str,
    events: list[dict],
) -> None:
    r = client.post(
        f"/api/v1/ai-systems/{system_id}/runtime-events",
        json={"events": events},
        headers={"x-api-key": API_KEY, "x-tenant-id": tenant_id},
    )
    assert r.status_code == 200, r.text


def test_event_source_supplier_label_de() -> None:
    assert event_source_supplier_label_de("sap_ai_core") == "SAP AI Core"
    assert "Custom" in event_source_supplier_label_de("manual_import")


def test_compute_drilldown_multi_system_mixed_sources() -> None:
    tid = f"drill-u-{uuid.uuid4().hex[:10]}"
    _create_system(tid, "sys-a", "System A")
    _create_system(tid, "sys-b", "System B")
    now = datetime.now(UTC)
    base = now.isoformat()
    _ingest_incidents(
        tid,
        "sys-a",
        [
            {
                "source_event_id": f"e-{uuid.uuid4().hex[:8]}-1",
                "source": "sap_ai_core",
                "event_type": "incident",
                "event_subtype": "safety_violation",
                "severity": "high",
                "occurred_at": base,
            },
            {
                "source_event_id": f"e-{uuid.uuid4().hex[:8]}-2",
                "source": "sap_ai_core",
                "event_type": "incident",
                "event_subtype": "safety_violation",
                "severity": "medium",
                "occurred_at": base,
            },
        ],
    )
    _ingest_incidents(
        tid,
        "sys-b",
        [
            {
                "source_event_id": f"e-{uuid.uuid4().hex[:8]}-3",
                "source": "manual_import",
                "event_type": "incident",
                "event_subtype": "availability_incident",
                "severity": "low",
                "occurred_at": base,
            },
        ],
    )
    with SessionLocal() as s:
        out = compute_tenant_incident_drilldown(s, tid, window_days=90)
    assert out.tenant_id == tid
    assert out.systems_with_incidents == 2
    assert len(out.items) == 2
    by_id = {x.ai_system_id: x for x in out.items}
    assert by_id["sys-a"].incident_total_90d == 2
    assert by_id["sys-a"].incident_count_by_category.safety == 2
    assert by_id["sys-a"].supplier_label_de == "SAP AI Core"
    assert by_id["sys-b"].incident_count_by_category.availability == 1
    lbl_b = by_id["sys-b"].supplier_label_de
    assert "Manuell" in lbl_b or "Custom" in lbl_b
    csv_text = tenant_incident_drilldown_to_csv(out)
    assert "ai_system_id" in csv_text
    assert "sys-a" in csv_text


def test_tenant_incident_drilldown_api_403_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY", "true")
    r = client.get(
        f"/api/v1/tenants/{T_OTHER}/incident-drilldown",
        headers={"x-api-key": API_KEY, "x-tenant-id": T_DRILL},
    )
    assert r.status_code == 403


def test_tenant_incident_drilldown_api_csv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY", "true")
    tid = f"drill-api-{uuid.uuid4().hex[:10]}"
    _create_system(tid, "sys-c", "C")
    now = datetime.now(UTC)
    _ingest_incidents(
        tid,
        "sys-c",
        [
            {
                "source_event_id": f"e-{uuid.uuid4().hex[:8]}",
                "source": "other_provider",
                "event_type": "incident",
                "event_subtype": "other_incident",
                "severity": "low",
                "occurred_at": now.isoformat(),
            },
        ],
    )
    r = client.get(
        f"/api/v1/tenants/{tid}/incident-drilldown",
        params={"format": "csv"},
        headers={"x-api-key": API_KEY, "x-tenant-id": tid},
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "sys-c" in r.text


def test_advisor_incident_drilldown_404_unlinked(
    advisor_allowlist: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_WORKSPACE", "true")
    r = client.get(
        f"/api/v1/advisors/{ADV_DR}/tenants/{T_OTHER}/incident-drilldown",
        headers=_adv_headers(),
    )
    assert r.status_code == 404


def test_advisor_incident_drilldown_200(
    advisor_allowlist: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_WORKSPACE", "true")
    _seed_advisor_link()
    _create_system(T_DRILL, "sys-d", "D")
    now = datetime.now(UTC)
    _ingest_incidents(
        T_DRILL,
        "sys-d",
        [
            {
                "source_event_id": f"e-{uuid.uuid4().hex[:8]}",
                "source": "sap_ai_core",
                "event_type": "incident",
                "event_subtype": "availability_incident",
                "severity": "medium",
                "occurred_at": now.isoformat(),
            },
        ],
    )
    r = client.get(
        f"/api/v1/advisors/{ADV_DR}/tenants/{T_DRILL}/incident-drilldown",
        headers=_adv_headers(),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant_id"] == T_DRILL
    assert body["systems_with_incidents"] >= 1
    assert len(body["items"]) >= 1
    assert body["items"][0]["ai_system_id"] == "sys-d"
