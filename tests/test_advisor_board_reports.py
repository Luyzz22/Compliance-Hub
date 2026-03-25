"""Advisor: AI-Compliance-Board-Reports nur für verknüpfte Mandanten."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.ai_compliance_board_reports import AiComplianceBoardReportRepository

client = TestClient(app)

ADV_A = "advisor-portfolio-a@example.com"
API_KEY = "board-kpi-key"
T1 = "adv-portfolio-tenant-1"
T3 = "adv-portfolio-tenant-3"


@pytest.fixture
def advisor_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "COMPLIANCEHUB_ADVISOR_IDS",
        f"{ADV_A},advisor-portfolio-b@example.com",
    )


def _adv_headers() -> dict[str, str]:
    return {"x-api-key": API_KEY, "x-advisor-id": ADV_A}


def _seed_link_t1() -> None:
    s = SessionLocal()
    try:
        AdvisorTenantRepository(s).upsert_link(
            advisor_id=ADV_A,
            tenant_id=T1,
            tenant_display_name="Alpha GmbH",
        )
    finally:
        s.close()


def _insert_report(tenant_id: str, title: str = "Test-Report") -> str:
    s = SessionLocal()
    try:
        repo = AiComplianceBoardReportRepository(s)
        row = repo.create(
            tenant_id=tenant_id,
            created_by=None,
            title=title,
            audience_type="board",
            raw_payload={"version": 1, "input": {}},
            rendered_markdown="# Board\n",
        )
        return row.id
    finally:
        s.close()


def test_advisor_board_reports_lists_only_linked_tenants(
    monkeypatch: pytest.MonkeyPatch,
    advisor_allowlist: None,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_WORKSPACE", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT", "true")
    _seed_link_t1()
    rid = _insert_report(T1)
    _insert_report(T3)

    r = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/board-reports",
        headers=_adv_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["advisor_id"] == ADV_A
    tids = {x["tenant_id"] for x in data["reports"]}
    assert T1 in tids
    assert T3 not in tids
    assert any(x["report_id"] == rid for x in data["reports"])


def test_advisor_board_report_detail_requires_link(
    monkeypatch: pytest.MonkeyPatch,
    advisor_allowlist: None,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_WORKSPACE", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT", "true")
    _seed_link_t1()
    rid = _insert_report(T1)

    r_ok = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/{T1}/board/ai-compliance-reports/{rid}",
        headers=_adv_headers(),
    )
    assert r_ok.status_code == 200
    assert r_ok.json()["rendered_markdown"].startswith("# Board")

    r_bad = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/{T3}/board/ai-compliance-reports/{rid}",
        headers=_adv_headers(),
    )
    assert r_bad.status_code == 404


def test_advisor_board_reports_forbidden_without_workspace_flag(
    monkeypatch: pytest.MonkeyPatch,
    advisor_allowlist: None,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_WORKSPACE", "false")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT", "true")
    r = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/board-reports",
        headers=_adv_headers(),
    )
    assert r.status_code == 403


def test_advisor_board_reports_forbidden_without_board_report_flag(
    monkeypatch: pytest.MonkeyPatch,
    advisor_allowlist: None,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_WORKSPACE", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT", "false")
    r = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/board-reports",
        headers=_adv_headers(),
    )
    assert r.status_code == 403
