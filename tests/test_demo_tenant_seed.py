"""Demo-Tenant-Seeding: API-Schutz, Counts, Tenant-Isolation, Advisor-Link."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.ai_governance_actions import AIGovernanceActionRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.classifications import ClassificationRepository
from app.repositories.evidence_files import EvidenceFileRepository
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository
from app.repositories.policies import PolicyRepository
from app.services.demo_tenant_seeder import seed_demo_tenant

client = TestClient(app)

DEMO_KEY = "demo-seed-key"
T1 = "demo-seed-tenant-1"
T2 = "demo-seed-tenant-2"
TA = "demo-isolation-a"
TB = "demo-isolation-b"
TD = "demo-direct-only"


def _demo_headers() -> dict[str, str]:
    return {"x-api-key": DEMO_KEY}


def test_list_demo_templates_requires_demo_key() -> None:
    r = client.get("/api/v1/demo/tenant-templates")
    assert r.status_code == 401


def test_list_demo_templates_ok() -> None:
    r = client.get("/api/v1/demo/tenant-templates", headers=_demo_headers())
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    keys = {x["key"] for x in data}
    assert keys == {"kritis_energy", "industrial_sme", "tax_advisor"}


def test_demo_seed_wrong_api_key() -> None:
    r = client.post(
        "/api/v1/demo/tenants/seed",
        headers={"x-api-key": "board-kpi-key"},
        json={"template_key": "kritis_energy", "tenant_id": T1},
    )
    assert r.status_code == 401


def test_demo_seed_tenant_not_allowlisted() -> None:
    r = client.post(
        "/api/v1/demo/tenants/seed",
        headers=_demo_headers(),
        json={"template_key": "kritis_energy", "tenant_id": "production-tenant-xyz"},
    )
    assert r.status_code == 403


def test_demo_seed_disabled_when_no_demo_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_DEMO_SEED_API_KEYS", "")
    r = client.get("/api/v1/demo/tenant-templates", headers=_demo_headers())
    assert r.status_code == 503


def test_post_demo_seed_creates_expected_entities() -> None:
    r = client.post(
        "/api/v1/demo/tenants/seed",
        headers=_demo_headers(),
        json={"template_key": "kritis_energy", "tenant_id": T1},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant_id"] == T1
    assert body["template_key"] == "kritis_energy"
    assert body["ai_systems_count"] == 4
    assert body["governance_actions_count"] == 5
    assert body["evidence_files_count"] == 3
    assert body["nis2_kpi_rows_count"] == 6
    assert body["policy_rows_count"] >= 1
    assert body["classifications_count"] == 4
    assert body["advisor_linked"] is False
    assert int(body.get("board_reports_count", 0)) >= 2
    assert int(body.get("ai_kpi_value_rows_count", 0)) >= 4
    assert int(body.get("cross_reg_control_rows_count", 0)) >= 1
    assert int(body.get("demo_governance_telemetry_events_inserted", 0)) >= 1
    assert int(body.get("demo_governance_runtime_events_inserted", 0)) >= 1
    assert body.get("demo_oami_snapshot_refreshed") is True

    r_layer = client.post(
        "/api/v1/demo/tenants/governance-maturity-layer",
        headers=_demo_headers(),
        json={"tenant_id": T1},
    )
    assert r_layer.status_code == 200, r_layer.text
    layer_body = r_layer.json()
    assert layer_body["telemetry_events_inserted"] == 0
    assert layer_body["runtime_events_inserted"] == 0
    assert layer_body["skipped_already_seeded"] is True

    meta = client.get(
        "/api/v1/workspace/tenant-meta",
        headers={"x-api-key": "board-kpi-key", "x-tenant-id": T1},
    )
    assert meta.status_code == 200, meta.text
    mj = meta.json()
    assert mj["is_demo"] is True
    assert mj["mutation_blocked"] is True
    assert mj["workspace_mode"] == "demo"
    assert "Demo" in mj["mode_label"]
    assert len(mj["mode_hint"]) > 10


def test_post_demo_seed_idempotent_conflict() -> None:
    r2 = client.post(
        "/api/v1/demo/tenants/seed",
        headers=_demo_headers(),
        json={"template_key": "industrial_sme", "tenant_id": T1},
    )
    assert r2.status_code == 409


def test_demo_seed_tenant_isolation() -> None:
    client.post(
        "/api/v1/demo/tenants/seed",
        headers=_demo_headers(),
        json={"template_key": "tax_advisor", "tenant_id": TA},
    )
    listed = client.get(
        "/api/v1/ai-systems",
        headers={"x-api-key": "board-kpi-key", "x-tenant-id": TB},
    )
    assert listed.status_code == 200
    assert listed.json() == []


def test_demo_seed_with_advisor_link() -> None:
    adv = "demo-advisor@example.com"
    r = client.post(
        "/api/v1/demo/tenants/seed",
        headers=_demo_headers(),
        json={"template_key": "industrial_sme", "tenant_id": T2, "advisor_id": adv},
    )
    assert r.status_code == 200, r.text
    assert r.json()["advisor_linked"] is True
    s = SessionLocal()
    try:
        link = AdvisorTenantRepository(s).get_link(adv, T2)
        assert link is not None
        assert link.tenant_id == T2
    finally:
        s.close()


def test_workspace_tenant_meta_not_registered() -> None:
    r = client.get(
        "/api/v1/workspace/tenant-meta",
        headers={
            "x-api-key": "board-kpi-key",
            "x-tenant-id": "unregistered-tenant-meta-xyz",
        },
    )
    assert r.status_code == 404


def test_seed_demo_tenant_does_not_touch_other_tenant() -> None:
    s = SessionLocal()
    try:
        ai = AISystemRepository(s)
        ta_count_before = len(ai.list_for_tenant(TA))
        assert ta_count_before > 0
        seed_demo_tenant(
            s,
            "tax_advisor",
            TD,
            advisor_id=None,
            ai_repo=ai,
            cls_repo=ClassificationRepository(s),
            nis2_repo=Nis2KritisKpiRepository(s),
            policy_repo=PolicyRepository(s),
            action_repo=AIGovernanceActionRepository(s),
            evidence_repo=EvidenceFileRepository(s),
        )
        assert len(ai.list_for_tenant(TA)) == ta_count_before
        assert len(ai.list_for_tenant(TD)) == 4
    finally:
        s.close()
