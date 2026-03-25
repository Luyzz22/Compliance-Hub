"""Pilot-Onboarding: Provisioning, mandantengebundene API-Keys, Usage-Events."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.feature_flags import FeatureFlag, is_feature_enabled
from app.main import app
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.usage_events import UsageEventRepository
from app.security import get_settings
from app.services.tenant_usage_metrics import compute_tenant_usage_metrics

client = TestClient(app)


def test_provision_tenant_sets_defaults_and_initial_key() -> None:
    r = client.post(
        "/api/v1/tenants/provision",
        headers={"x-api-key": "provision-admin-test-key"},
        json={
            "tenant_name": "Pilot GmbH",
            "industry": "Fertigung",
            "country": "DE",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"].startswith("pilot-")
    assert body["display_name"] == "Pilot GmbH"
    flags = body["feature_flags"]
    assert flags["advisor_workspace"] is False
    assert flags["demo_seeding"] is False
    assert flags["guided_setup"] is True
    assert flags["evidence_uploads"] is True
    assert flags.get("pilot_runbook") is True
    assert flags.get("api_keys_ui") is True
    assert flags.get("llm_enabled") is False
    assert flags.get("llm_legal_reasoning") is False
    assert flags.get("llm_kpi_suggestions") is False
    assert flags.get("llm_explain") is False
    assert flags.get("llm_action_drafts") is False
    ikey = body["initial_api_key"]
    assert ikey["name"] == "Initial Pilot Key"
    assert len(ikey["plain_key"]) > 20
    assert body["advisor_linked"] is False
    assert body["demo_seeded"] is False

    tid = body["tenant_id"]
    plain = ikey["plain_key"]

    listed = client.get(
        f"/api/v1/tenants/{tid}/api-keys",
        headers={"x-api-key": plain, "x-tenant-id": tid},
    )
    assert listed.status_code == 200
    keys = listed.json()
    assert len(keys) == 1
    assert keys[0]["name"] == "Initial Pilot Key"
    assert keys[0]["active"] is True


def test_db_api_key_wrong_tenant_rejected() -> None:
    r = client.post(
        "/api/v1/tenants/provision",
        headers={"x-api-key": "provision-admin-test-key"},
        json={"tenant_name": "A", "industry": "B", "country": "DE"},
    )
    key_a = r.json()["initial_api_key"]["plain_key"]

    r2 = client.post(
        "/api/v1/tenants/provision",
        headers={"x-api-key": "provision-admin-test-key"},
        json={"tenant_name": "C", "industry": "D", "country": "DE"},
    )
    tid_b = r2.json()["tenant_id"]

    bad = client.get(
        f"/api/v1/tenants/{tid_b}/api-keys",
        headers={"x-api-key": key_a, "x-tenant-id": tid_b},
    )
    assert bad.status_code == 401


def test_provision_with_advisor_link() -> None:
    aid = "advisor-pilot@example.com"
    r = client.post(
        "/api/v1/tenants/provision",
        headers={"x-api-key": "provision-admin-test-key"},
        json={
            "tenant_name": "Beraten AG",
            "industry": "IT",
            "country": "DE",
            "advisor_id": aid,
        },
    )
    assert r.status_code == 200
    assert r.json()["advisor_linked"] is True
    tid = r.json()["tenant_id"]
    s = SessionLocal()
    try:
        repo = AdvisorTenantRepository(s)
        link = repo.get_link(aid, tid)
        assert link is not None
        assert link.tenant_display_name == "Beraten AG"
    finally:
        s.close()


def test_provision_rejects_invalid_admin_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ADMIN_API_KEYS", "only-real-admin")
    get_settings.cache_clear()
    r = client.post(
        "/api/v1/tenants/provision",
        headers={"x-api-key": "wrong"},
        json={"tenant_name": "X", "industry": "Y", "country": "DE"},
    )
    assert r.status_code == 401


def test_create_and_revoke_api_key() -> None:
    r = client.post(
        "/api/v1/tenants/provision",
        headers={"x-api-key": "provision-admin-test-key"},
        json={"tenant_name": "KeyOps", "industry": "X", "country": "DE"},
    )
    tid = r.json()["tenant_id"]
    plain = r.json()["initial_api_key"]["plain_key"]

    cr = client.post(
        f"/api/v1/tenants/{tid}/api-keys",
        headers={"x-api-key": plain, "x-tenant-id": tid},
        json={"name": "ETL Produktiv"},
    )
    assert cr.status_code == 200
    kid = cr.json()["id"]
    plain2 = cr.json()["plain_key"]

    listed = client.get(
        f"/api/v1/tenants/{tid}/api-keys",
        headers={"x-api-key": plain2, "x-tenant-id": tid},
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 2

    dl = client.delete(
        f"/api/v1/tenants/{tid}/api-keys/{kid}",
        headers={"x-api-key": plain2, "x-tenant-id": tid},
    )
    assert dl.status_code == 204

    listed2 = client.get(
        f"/api/v1/tenants/{tid}/api-keys",
        headers={"x-api-key": plain, "x-tenant-id": tid},
    )
    rows = listed2.json()
    revoked = next(x for x in rows if x["id"] == kid)
    assert revoked["active"] is False


def test_provision_logs_usage_event() -> None:
    monkeypatch_local = pytest.MonkeyPatch()
    monkeypatch_local.setenv("COMPLIANCEHUB_USAGE_TRACKING", "true")
    tid_marker = None
    try:
        r = client.post(
            "/api/v1/tenants/provision",
            headers={"x-api-key": "provision-admin-test-key"},
            json={"tenant_name": "Usage Co", "industry": "Z", "country": "DE"},
        )
        assert r.status_code == 200
        tid_marker = r.json()["tenant_id"]
        s = SessionLocal()
        try:
            m = compute_tenant_usage_metrics(s, tid_marker)
            assert m.tenant_id == tid_marker
            repo = UsageEventRepository(s)
            from datetime import UTC, datetime, timedelta

            since = datetime.now(UTC) - timedelta(minutes=5)
            c = repo.count_by_type_since(
                tid_marker,
                ["tenant_provisioned"],
                since=since,
            )
            assert c.get("tenant_provisioned", 0) >= 1
        finally:
            s.close()
    finally:
        monkeypatch_local.undo()


def test_tenant_feature_override_beats_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mandanten-Override aus Provisioning bleibt aktiv, auch wenn ENV das Feature aus hat."""
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GUIDED_SETUP", "false")
    get_settings.cache_clear()
    r = client.post(
        "/api/v1/tenants/provision",
        headers={"x-api-key": "provision-admin-test-key"},
        json={"tenant_name": "O", "industry": "P", "country": "DE"},
    )
    assert r.status_code == 200
    tid = r.json()["tenant_id"]
    s = SessionLocal()
    try:
        assert is_feature_enabled(FeatureFlag.guided_setup, tid, session=s) is True
    finally:
        s.close()
