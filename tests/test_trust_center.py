"""Tests for Trust Center & Assurance Portal API endpoints and service."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.models_db import Base

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def _engine(tmp_path):
    db_path = tmp_path / "trust_center_test.db"
    url = f"sqlite+pysqlite:///{db_path}"
    engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def _session(_engine):
    sm = sessionmaker(bind=_engine)
    session = sm()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# DB model / migration tests
# ---------------------------------------------------------------------------


def test_trust_center_tables_exist(_engine) -> None:
    """All three trust center tables are created."""
    inspector = inspect(_engine)
    assert inspector.has_table("trust_center_assets")
    assert inspector.has_table("evidence_bundles")
    assert inspector.has_table("trust_center_access_logs")


def test_migration_satisfied(_engine) -> None:
    from app.db_migrations.migrations.m20260419_trust_center_assurance_portal import (
        satisfied,
    )

    assert satisfied(_engine)


def test_migration_apply_idempotent(_engine) -> None:
    from app.db_migrations.migrations.m20260419_trust_center_assurance_portal import (
        apply,
    )

    assert apply(_engine) is False  # tables already exist via create_all


# ---------------------------------------------------------------------------
# Service-layer tests
# ---------------------------------------------------------------------------


def test_public_trust_center_content() -> None:
    from app.services.trust_center_service import get_public_trust_center_content

    content = get_public_trust_center_content()
    assert "security_overview" in content
    assert "compliance_overview" in content
    assert "data_residency" in content
    assert "subprocessors" in content
    assert "responsible_disclosure" in content
    assert len(content["compliance_overview"]["frameworks"]) == 6


def test_create_and_list_assets(_session) -> None:
    from app.services.trust_center_service import (
        create_trust_center_asset,
        list_trust_center_assets,
    )

    asset = create_trust_center_asset(
        _session,
        "tenant-tc-001",
        {
            "title": "ISMS Policy v2",
            "description": "Information Security Management System Policy",
            "asset_type": "policy",
            "sensitivity": "customer",
            "framework_refs": ["ISO_27001", "NIS2"],
            "published": True,
        },
    )
    assert asset["id"]
    assert asset["title"] == "ISMS Policy v2"
    assert asset["published"] is True

    assets = list_trust_center_assets(_session, "tenant-tc-001")
    assert len(assets) == 1
    assert assets[0]["id"] == asset["id"]


def test_list_assets_sensitivity_filter(_session) -> None:
    from app.services.trust_center_service import (
        create_trust_center_asset,
        list_trust_center_assets,
    )

    # Create assets with different sensitivity levels
    create_trust_center_asset(
        _session,
        "tenant-tc-002",
        {"title": "Public Doc", "sensitivity": "public", "published": True},
    )
    create_trust_center_asset(
        _session,
        "tenant-tc-002",
        {"title": "Auditor Doc", "sensitivity": "auditor", "published": True},
    )
    create_trust_center_asset(
        _session,
        "tenant-tc-002",
        {"title": "Internal Doc", "sensitivity": "internal", "published": True},
    )

    # Prospect sees only public
    public_only = list_trust_center_assets(_session, "tenant-tc-002", sensitivity_max="public")
    assert len(public_only) == 1
    assert public_only[0]["title"] == "Public Doc"

    # Customer sees public + prospect + customer (no auditor docs created)
    customer = list_trust_center_assets(_session, "tenant-tc-002", sensitivity_max="customer")
    assert len(customer) == 1

    # Auditor sees up to auditor
    auditor = list_trust_center_assets(_session, "tenant-tc-002", sensitivity_max="auditor")
    assert len(auditor) == 2

    # Internal sees all
    internal = list_trust_center_assets(_session, "tenant-tc-002", sensitivity_max="internal")
    assert len(internal) == 3


def test_update_asset(_session) -> None:
    from app.services.trust_center_service import (
        create_trust_center_asset,
        update_trust_center_asset,
    )

    asset = create_trust_center_asset(
        _session,
        "tenant-tc-003",
        {"title": "Draft Policy", "published": False},
    )
    updated = update_trust_center_asset(
        _session,
        "tenant-tc-003",
        asset["id"],
        {"title": "Final Policy", "published": True},
    )
    assert updated is not None
    assert updated["title"] == "Final Policy"
    assert updated["published"] is True


def test_update_asset_not_found(_session) -> None:
    from app.services.trust_center_service import update_trust_center_asset

    result = update_trust_center_asset(_session, "tenant-tc-004", "nonexistent-id", {"title": "X"})
    assert result is None


def test_generate_and_list_bundles(_session) -> None:
    from app.services.trust_center_service import (
        generate_evidence_bundle,
        list_evidence_bundles,
    )

    bundle = generate_evidence_bundle(_session, "tenant-tc-005", "iso_27001")
    assert bundle["id"]
    assert bundle["bundle_type"] == "iso_27001"
    assert bundle["title"] == "ISO 27001 Evidence Bundle"
    assert "frameworks" in bundle["metadata"]

    bundles = list_evidence_bundles(_session, "tenant-tc-005")
    assert len(bundles) == 1


def test_generate_bundle_includes_matching_assets(_session) -> None:
    from app.services.trust_center_service import (
        create_trust_center_asset,
        generate_evidence_bundle,
    )

    create_trust_center_asset(
        _session,
        "tenant-tc-006",
        {
            "title": "ISO Policy",
            "framework_refs": ["ISO_27001"],
            "published": True,
        },
    )
    create_trust_center_asset(
        _session,
        "tenant-tc-006",
        {
            "title": "DSGVO Doc",
            "framework_refs": ["DSGVO"],
            "published": True,
        },
    )

    bundle = generate_evidence_bundle(_session, "tenant-tc-006", "iso_27001")
    assert len(bundle["artefact_ids"]) == 1  # only ISO asset matches

    all_bundle = generate_evidence_bundle(_session, "tenant-tc-006", "auditor_bundle")
    assert len(all_bundle["artefact_ids"]) == 2  # all assets


def test_get_evidence_bundle(_session) -> None:
    from app.services.trust_center_service import (
        generate_evidence_bundle,
        get_evidence_bundle,
    )

    bundle = generate_evidence_bundle(_session, "tenant-tc-007", "nis2")
    fetched = get_evidence_bundle(_session, "tenant-tc-007", bundle["id"])
    assert fetched is not None
    assert fetched["bundle_type"] == "nis2"


def test_compliance_mapping_overview(_session) -> None:
    from app.services.trust_center_service import (
        create_trust_center_asset,
        get_compliance_mapping_overview,
    )

    create_trust_center_asset(
        _session,
        "tenant-tc-008",
        {
            "title": "Access Control",
            "framework_refs": ["ISO_27001", "NIS2", "DSGVO"],
            "published": True,
        },
    )
    create_trust_center_asset(
        _session,
        "tenant-tc-008",
        {
            "title": "AI Register",
            "framework_refs": ["EU_AI_ACT", "ISO_42001"],
            "published": True,
        },
    )

    mapping = get_compliance_mapping_overview(_session, "tenant-tc-008")
    assert mapping["total_controls"] == 2
    assert len(mapping["frameworks"]) == 6
    assert len(mapping["controls"]) == 2
    assert mapping["framework_coverage"]["ISO_27001"] == 0.5
    assert mapping["framework_coverage"]["EU_AI_ACT"] == 0.5


def test_access_logging(_session) -> None:
    from app.models_db import TrustCenterAccessLogDB
    from app.services.trust_center_service import log_trust_center_access

    log_trust_center_access(
        _session,
        tenant_id="tenant-tc-009",
        actor="user@example.com",
        role="auditor",
        action="download_asset",
        resource_type="trust_center_asset",
        resource_id="asset-123",
        ip_address="192.168.1.1",
    )

    logs = (
        _session.query(TrustCenterAccessLogDB)
        .filter(TrustCenterAccessLogDB.tenant_id == "tenant-tc-009")
        .all()
    )
    assert len(logs) == 1
    assert logs[0].action == "download_asset"
    assert logs[0].actor == "user@example.com"
    assert logs[0].ip_address == "192.168.1.1"


def test_tenant_isolation(_session) -> None:
    from app.services.trust_center_service import (
        create_trust_center_asset,
        get_trust_center_asset,
        list_trust_center_assets,
    )

    asset = create_trust_center_asset(
        _session,
        "tenant-A",
        {"title": "Tenant A Doc", "published": True},
    )

    # Tenant B should not see tenant A's assets
    tenant_b_assets = list_trust_center_assets(_session, "tenant-B")
    assert len(tenant_b_assets) == 0

    # Direct access by tenant B should return None
    result = get_trust_center_asset(_session, "tenant-B", asset["id"])
    assert result is None


# ---------------------------------------------------------------------------
# RBAC permission tests
# ---------------------------------------------------------------------------


def test_trust_center_permissions_viewer() -> None:
    from app.rbac.permissions import Permission, has_permission
    from app.rbac.roles import EnterpriseRole

    assert has_permission(EnterpriseRole.VIEWER, Permission.VIEW_TRUST_CENTER)
    assert not has_permission(EnterpriseRole.VIEWER, Permission.MANAGE_TRUST_CENTER)
    assert not has_permission(EnterpriseRole.VIEWER, Permission.ACCESS_EVIDENCE_BUNDLES)
    assert not has_permission(EnterpriseRole.VIEWER, Permission.DOWNLOAD_ASSURANCE_DOCS)


def test_trust_center_permissions_contributor() -> None:
    from app.rbac.permissions import Permission, has_permission
    from app.rbac.roles import EnterpriseRole

    assert has_permission(EnterpriseRole.CONTRIBUTOR, Permission.VIEW_TRUST_CENTER)
    assert has_permission(EnterpriseRole.CONTRIBUTOR, Permission.DOWNLOAD_ASSURANCE_DOCS)
    assert not has_permission(EnterpriseRole.CONTRIBUTOR, Permission.ACCESS_EVIDENCE_BUNDLES)


def test_trust_center_permissions_auditor() -> None:
    from app.rbac.permissions import Permission, has_permission
    from app.rbac.roles import EnterpriseRole

    assert has_permission(EnterpriseRole.AUDITOR, Permission.VIEW_TRUST_CENTER)
    assert has_permission(EnterpriseRole.AUDITOR, Permission.DOWNLOAD_ASSURANCE_DOCS)
    assert has_permission(EnterpriseRole.AUDITOR, Permission.ACCESS_EVIDENCE_BUNDLES)
    assert not has_permission(EnterpriseRole.AUDITOR, Permission.MANAGE_TRUST_CENTER)


def test_trust_center_permissions_compliance_admin() -> None:
    from app.rbac.permissions import Permission, has_permission
    from app.rbac.roles import EnterpriseRole

    assert has_permission(EnterpriseRole.COMPLIANCE_ADMIN, Permission.MANAGE_TRUST_CENTER)
    assert has_permission(EnterpriseRole.COMPLIANCE_ADMIN, Permission.ACCESS_EVIDENCE_BUNDLES)


def test_trust_center_permissions_tenant_admin() -> None:
    from app.rbac.permissions import Permission, has_permission
    from app.rbac.roles import EnterpriseRole

    assert has_permission(EnterpriseRole.TENANT_ADMIN, Permission.VIEW_TRUST_CENTER)
    assert has_permission(EnterpriseRole.TENANT_ADMIN, Permission.MANAGE_TRUST_CENTER)
    assert has_permission(EnterpriseRole.TENANT_ADMIN, Permission.ACCESS_EVIDENCE_BUNDLES)
    assert has_permission(EnterpriseRole.TENANT_ADMIN, Permission.DOWNLOAD_ASSURANCE_DOCS)


# ---------------------------------------------------------------------------
# API endpoint tests (via TestClient)
# ---------------------------------------------------------------------------


def test_api_public_trust_center() -> None:
    """Public endpoint returns trust center content without auth."""
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/trust-center/public")
    assert resp.status_code == 200
    data = resp.json()
    assert "security_overview" in data
    assert "compliance_overview" in data


def test_api_bundle_types() -> None:
    """Bundle types endpoint is public."""
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/trust-center/bundle-types")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["bundle_types"]) == 7


def test_api_list_assets_requires_auth() -> None:
    """Gated endpoints return 401/403 without proper auth."""
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/trust-center/assets")
    # Without API key, should fail
    assert resp.status_code in (400, 401, 403, 422)


def test_api_generate_bundle_invalid_type() -> None:
    """Generate bundle with invalid type returns 400."""
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post(
        "/api/v1/trust-center/evidence-bundles/generate",
        json={"bundle_type": "invalid_type"},
        headers={
            "x-api-key": "test-key",
            "x-tenant-id": "test-tenant",
            "x-opa-user-role": "compliance_admin",
        },
    )
    assert resp.status_code == 400


def test_api_compliance_mapping_requires_auth() -> None:
    """Compliance mapping endpoint requires auth."""
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/trust-center/compliance-mapping")
    assert resp.status_code in (400, 401, 403, 422)
