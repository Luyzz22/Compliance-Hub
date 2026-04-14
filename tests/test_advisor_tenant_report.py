"""Mandanten-Steckbrief: build_service, GET report JSON/Markdown, Advisor-Tenant-Isolation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.ai_governance_actions import AIGovernanceActionRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.classifications import ClassificationRepository
from app.repositories.compliance_gap import ComplianceGapRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository
from app.repositories.violations import ViolationRepository
from app.services.advisor_tenant_report import build_advisor_tenant_report
from app.services.advisor_tenant_report_markdown import render_tenant_report_markdown

client = TestClient(app)

ADV_A = "advisor-report-a@example.com"
ADV_B = "advisor-report-b@example.com"
API_KEY = "board-kpi-key"
R1 = "adv-report-tenant-1"
R2 = "adv-report-tenant-2"


@pytest.fixture
def advisor_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ADVISOR_IDS", f"{ADV_A},{ADV_B}")


def _adv_headers(advisor_id: str) -> dict[str, str]:
    return {"x-api-key": API_KEY, "x-advisor-id": advisor_id}


def _seed_links() -> None:
    s = SessionLocal()
    try:
        r = AdvisorTenantRepository(s)
        r.upsert_link(
            advisor_id=ADV_A,
            tenant_id=R1,
            tenant_display_name="Report Demo GmbH",
            industry="Manufacturing",
            country="DE",
        )
        r.upsert_link(
            advisor_id=ADV_B,
            tenant_id=R2,
            tenant_display_name="Other",
            industry=None,
            country="CH",
        )
    finally:
        s.close()


def _tenant_headers(tenant_id: str) -> dict[str, str]:
    return {
        "x-api-key": API_KEY,
        "x-tenant-id": tenant_id,
        "x-opa-user-role": "compliance_officer",
    }


def _post_system(tenant_id: str, system_id: str, risk: str = "high") -> None:
    body = {
        "id": system_id,
        "name": f"Sys {system_id}",
        "description": "p",
        "business_unit": "IT",
        "risk_level": risk,
        "ai_act_category": "high_risk" if risk == "high" else "minimal_risk",
        "gdpr_dpia_required": risk == "high",
        "owner_email": "o@example.com",
        "criticality": "medium",
        "data_sensitivity": "internal",
        "has_incident_runbook": True,
        "has_supplier_risk_register": True,
        "has_backup_runbook": True,
    }
    resp = client.post(
        "/api/v1/ai-systems",
        json=body,
        headers=_tenant_headers(tenant_id),
    )
    assert resp.status_code == 200, resp.text


def _post_action(tenant_id: str, system_id: str, *, overdue: bool = False) -> None:
    payload: dict = {
        "related_ai_system_id": system_id,
        "related_requirement": "EU AI Act Art. 9",
        "title": "Dokumentation",
        "status": "open",
    }
    if overdue:
        payload["due_date"] = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    resp = client.post(
        "/api/v1/ai-governance/actions",
        headers=_tenant_headers(tenant_id),
        json=payload,
    )
    assert resp.status_code == 201, resp.text


def test_build_advisor_tenant_report_aggregates(advisor_allowlist: None) -> None:
    _seed_links()
    _post_system(R1, "rep-sys-1", "high")
    _post_system(R1, "rep-sys-2", "low")
    _post_action(R1, "rep-sys-1", overdue=True)
    _post_action(R1, "rep-sys-1", overdue=False)

    s = SessionLocal()
    try:
        adv_repo = AdvisorTenantRepository(s)
        link = adv_repo.get_link(ADV_A, R1)
        assert link is not None
        report = build_advisor_tenant_report(
            s,
            R1,
            link=link,
            ai_repo=AISystemRepository(s),
            cls_repo=ClassificationRepository(s),
            gap_repo=ComplianceGapRepository(s),
            nis2_repo=Nis2KritisKpiRepository(s),
            violation_repo=ViolationRepository(s),
            action_repo=AIGovernanceActionRepository(s),
            incident_repo=IncidentRepository(s),
        )
    finally:
        s.close()

    assert report.tenant_id == R1
    assert report.tenant_name == "Report Demo GmbH"
    assert report.industry == "Manufacturing"
    assert report.country == "DE"
    assert report.ai_systems_total == 2
    assert report.high_risk_systems_count >= 1
    assert 0.0 <= report.eu_ai_act_readiness_score <= 1.0
    assert report.eu_ai_act_days_remaining >= 0
    assert report.governance_open_actions_count >= 2
    assert report.governance_overdue_actions_count >= 1
    assert report.setup_total_steps == 7
    assert len(report.top_critical_requirements) <= 3


def test_get_advisor_tenant_report_json(advisor_allowlist: None) -> None:
    _seed_links()
    _post_system(R1, "rep-json-1", "low")

    res = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/{R1}/report?format=json",
        headers=_adv_headers(ADV_A),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["tenant_id"] == R1
    assert "tenant_name" in data
    assert "eu_ai_act_readiness_score" in data
    assert "nis2_incident_readiness_percent" in data
    assert "setup_completed_steps" in data
    assert "risiko_incidents_90d_count" in data
    assert "risiko_incident_burden_level" in data


def test_get_advisor_tenant_report_markdown(advisor_allowlist: None) -> None:
    _seed_links()
    _post_system(R1, "rep-md-1", "low")

    res = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/{R1}/report?format=markdown",
        headers=_adv_headers(ADV_A),
    )
    assert res.status_code == 200, res.text
    assert "text/markdown" in res.headers.get("content-type", "")
    cd = res.headers.get("content-disposition", "")
    assert "attachment" in cd.lower()
    assert f"tenant-report-{R1}" in cd
    text = res.content.decode("utf-8")
    assert text.startswith("# Compliance Hub Mandanten-Steckbrief")
    assert "## Profil" in text
    assert "## EU AI Act" in text
    assert "## NIS2 / KRITIS" in text
    assert "## Governance und Maßnahmen" in text
    assert "## Risiko- und Incident-Lage (NIS2/KRITIS)" in text


def test_advisor_tenant_report_not_linked_404(advisor_allowlist: None) -> None:
    _seed_links()
    res = client.get(
        f"/api/v1/advisors/{ADV_B}/tenants/{R1}/report?format=json",
        headers=_adv_headers(ADV_B),
    )
    assert res.status_code == 404


def test_render_tenant_report_markdown_structure() -> None:
    from app.advisor_models import AdvisorTenantReport, TenantReportCriticalRequirementItem

    r = AdvisorTenantReport(
        tenant_id="t-x",
        tenant_name="X AG",
        industry="IT",
        country="DE",
        generated_at_utc=datetime.now(UTC),
        ai_systems_total=3,
        high_risk_systems_count=1,
        high_risk_with_full_controls_count=0,
        eu_ai_act_readiness_score=0.5,
        eu_ai_act_deadline="2026-08-02",
        eu_ai_act_days_remaining=100,
        nis2_incident_readiness_percent=80.0,
        nis2_supplier_risk_coverage_percent=70.0,
        nis2_ot_it_segregation_mean_percent=60.0,
        nis2_critical_focus_systems_count=0,
        governance_open_actions_count=2,
        governance_overdue_actions_count=1,
        top_critical_requirements=[
            TenantReportCriticalRequirementItem(code="C1", name="Gap", affected_systems_count=1),
        ],
        setup_completed_steps=4,
        setup_total_steps=7,
        setup_open_step_labels=["KI-Inventar"],
    )
    md = render_tenant_report_markdown(r)
    assert "X AG" in md
    assert "EU AI Act" in md
    assert "C1" in md
    assert "## Risiko- und Incident-Lage (NIS2/KRITIS)" in md
