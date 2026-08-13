"""Advisor-Portfolio-API: Mandantenliste, KPI-Aggregation, Isolation, Export."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models_db import TenantDB
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.users import UserRepository
from app.services.identity_service import IdentityService

client = TestClient(app)

ADV_A = "advisor-portfolio-a@example.com"
ADV_B = "advisor-portfolio-b@example.com"
API_KEY = "board-kpi-key"
T1 = "adv-portfolio-tenant-1"
T2 = "adv-portfolio-tenant-2"
T3 = "adv-portfolio-tenant-3"
BFF_SECRET = "advisor-test-bff-secret-at-least-32-bytes"


@pytest.fixture
def advisor_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "COMPLIANCEHUB_ADVISOR_IDS",
        f"{ADV_A},{ADV_B}",
    )


def _adv_headers(advisor_id: str) -> dict[str, str]:
    return {
        "x-api-key": API_KEY,
        "x-advisor-id": advisor_id,
    }


def _advisor_session(email: str, *, role: str = "advisor") -> str:
    tenant_id = f"advisor-firm-{uuid.uuid4().hex}"
    with SessionLocal() as session:
        identity = IdentityService(UserRepository(session))
        registered = identity.register(email=email, password="EnterprisePass123")
        verified = identity.verify_email(registered["verification_token"])
        identity.assign_role(verified["user_id"], tenant_id, role, assigned_by="test")
    response = client.post(
        "/api/v1/auth/session/login",
        headers={"x-bff-secret": BFF_SECRET},
        json={
            "email": email,
            "password": "EnterprisePass123",
            "tenant_id": tenant_id,
        },
    )
    assert response.status_code == 200, response.text
    return str(response.json()["session_token"])


def _ensure_tenant_registry_row(
    tenant_id: str,
    *,
    nis2_scope: str = "in_scope",
    kritis_sector: str | None = None,
) -> None:
    """Stammdaten für Portfolio-NIS2/KRITIS-Felder (Tests)."""
    s = SessionLocal()
    try:
        row = s.get(TenantDB, tenant_id)
        if row is None:
            s.add(
                TenantDB(
                    id=tenant_id,
                    display_name=tenant_id,
                    industry="Energie",
                    country="DE",
                    nis2_scope=nis2_scope,
                    kritis_sector=kritis_sector,
                    ai_act_scope="in_scope",
                    created_at_utc=datetime.now(UTC),
                ),
            )
        else:
            row.nis2_scope = nis2_scope
            row.kritis_sector = kritis_sector
        s.commit()
    finally:
        s.close()


def _seed_links() -> None:
    s = SessionLocal()
    try:
        r = AdvisorTenantRepository(s)
        r.upsert_link(
            advisor_id=ADV_A,
            tenant_id=T1,
            tenant_display_name="Alpha GmbH",
            industry="Manufacturing",
            country="DE",
        )
        r.upsert_link(
            advisor_id=ADV_A,
            tenant_id=T2,
            tenant_display_name="Beta AG",
            industry="Services",
            country="AT",
        )
        r.upsert_link(
            advisor_id=ADV_B,
            tenant_id=T3,
            tenant_display_name="Gamma KG",
            industry="Finance",
            country="CH",
        )
    finally:
        s.close()


def _post_min_system(tenant_id: str, system_id: str, risk: str = "low") -> None:
    body = {
        "id": system_id,
        "name": f"System {system_id}",
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
    r = client.post(
        "/api/v1/ai-systems",
        json=body,
        headers={"x-api-key": API_KEY, "x-tenant-id": tenant_id},
    )
    assert r.status_code == 200, r.text


def test_advisor_portfolio_returns_only_linked_tenants(advisor_allowlist: None) -> None:
    _seed_links()
    _post_min_system(T1, "s1", "high")
    _post_min_system(T2, "s2", "low")

    res = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/portfolio",
        headers=_adv_headers(ADV_A),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["advisor_id"] == ADV_A
    assert len(data["tenants"]) == 2
    ids = {t["tenant_id"] for t in data["tenants"]}
    assert ids == {T1, T2}
    alpha = next(t for t in data["tenants"] if t["tenant_id"] == T1)
    assert alpha["tenant_name"] == "Alpha GmbH"
    assert alpha["industry"] == "Manufacturing"
    assert alpha["country"] == "DE"
    assert alpha["high_risk_systems_count"] >= 1
    assert 0.0 <= alpha["eu_ai_act_readiness"] <= 1.0
    assert alpha["setup_total_steps"] == 7


def test_advisor_portfolio_forbidden_header_mismatch(advisor_allowlist: None) -> None:
    _seed_links()
    r = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/portfolio",
        headers=_adv_headers(ADV_B),
    )
    assert r.status_code == 403


def test_advisor_b_does_not_see_advisor_a_tenants(advisor_allowlist: None) -> None:
    _seed_links()
    res = client.get(
        f"/api/v1/advisors/{ADV_B}/tenants/portfolio",
        headers=_adv_headers(ADV_B),
    )
    assert res.status_code == 200
    ids = {t["tenant_id"] for t in res.json()["tenants"]}
    assert ids == {T3}
    assert T1 not in ids and T2 not in ids


def test_advisor_not_in_allowlist_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ADVISOR_IDS", "only-other@example.com")
    r = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/portfolio",
        headers=_adv_headers(ADV_A),
    )
    assert r.status_code == 403


def test_advisor_user_session_is_bound_to_verified_email_and_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    advisor_id = f"advisor-session-{uuid.uuid4().hex}@example.com"
    monkeypatch.setenv("COMPLIANCEHUB_ADVISOR_IDS", advisor_id)
    monkeypatch.setenv("COMPLIANCEHUB_BFF_SHARED_SECRET", BFF_SECRET)
    token = _advisor_session(advisor_id)

    allowed = client.get(
        f"/api/v1/advisors/{advisor_id}/tenants/portfolio",
        headers={"Authorization": f"Bearer {token}"},
    )
    mismatch = client.get(
        f"/api/v1/advisors/{ADV_B}/tenants/portfolio",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert allowed.status_code == 200, allowed.text
    assert mismatch.status_code == 403


def test_non_advisor_user_session_cannot_open_advisor_portfolio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    advisor_id = f"viewer-session-{uuid.uuid4().hex}@example.com"
    monkeypatch.setenv("COMPLIANCEHUB_ADVISOR_IDS", advisor_id)
    monkeypatch.setenv("COMPLIANCEHUB_BFF_SHARED_SECRET", BFF_SECRET)
    token = _advisor_session(advisor_id, role="viewer")

    response = client.get(
        f"/api/v1/advisors/{advisor_id}/tenants/portfolio",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_advisor_portfolio_includes_nis2_kritis_incident_fields(advisor_allowlist: None) -> None:
    _ensure_tenant_registry_row(
        T1,
        nis2_scope="essential_entity",
        kritis_sector="energy",
    )
    _seed_links()
    _post_min_system(T1, "sx", "low")

    res = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/portfolio",
        headers=_adv_headers(ADV_A),
    )
    assert res.status_code == 200, res.text
    alpha = next(t for t in res.json()["tenants"] if t["tenant_id"] == T1)
    assert alpha["nis2_entity_category"] == "essential_entity"
    assert alpha["kritis_sector_key"] == "energy"
    assert alpha["recent_incidents_90d"] is False
    assert alpha["incident_burden_level"] == "low"


def test_advisor_portfolio_export_json_and_csv(advisor_allowlist: None) -> None:
    _ensure_tenant_registry_row(T1)
    _seed_links()
    _post_min_system(T1, "sys-export-csv", "low")

    jr = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/portfolio-export?format=json",
        headers=_adv_headers(ADV_A),
    )
    assert jr.status_code == 200
    assert "application/json" in jr.headers.get("content-type", "")
    payload = json.loads(jr.content.decode("utf-8"))
    assert payload["advisor_id"] == ADV_A
    assert len(payload["tenants"]) == 2

    cr = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/portfolio-export?format=csv",
        headers=_adv_headers(ADV_A),
    )
    assert cr.status_code == 200
    rows = list(csv.DictReader(io.StringIO(cr.content.decode("utf-8"))))
    assert len(rows) == 2
    assert set(rows[0].keys()) >= {
        "tenant_id",
        "eu_ai_act_readiness",
        "setup_progress_ratio",
        "nis2_entity_category",
        "kritis_sector_key",
        "recent_incidents_90d",
        "incident_burden_level",
        "advisor_priority",
        "advisor_priority_explanation_de",
    }
