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


# ---------------------------------------------------------------------------
# Phase 14 – Health Endpoint Auth-Gate Tests
# ---------------------------------------------------------------------------


def test_health_endpoint_no_role_returns_403() -> None:
    """Health endpoint returns 403 for anonymous/default CONTRIBUTOR role."""
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/trust-center/health")
    assert resp.status_code == 403


def test_health_endpoint_viewer_returns_403() -> None:
    """Health endpoint returns 403 for viewer role (insufficient permission)."""
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(
        "/api/v1/trust-center/health",
        headers={"x-opa-user-role": "viewer"},
    )
    assert resp.status_code == 403


def test_health_endpoint_compliance_admin_returns_200() -> None:
    """Health endpoint returns 200 for compliance_admin role."""
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(
        "/api/v1/trust-center/health",
        headers={"x-opa-user-role": "compliance_admin"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "registry_configured" in data


# ---------------------------------------------------------------------------
# Phase 11 – Sensitivity Gate & E-Signing Tests
# ---------------------------------------------------------------------------


def test_get_asset_blocks_unpublished(_session) -> None:
    """P1 Fix: get_trust_center_asset returns None for unpublished assets."""
    from app.services.trust_center_service import (
        create_trust_center_asset,
        get_trust_center_asset,
    )

    asset = create_trust_center_asset(
        _session,
        "tenant-p11-01",
        {"title": "Draft Doc", "sensitivity": "public", "published": False},
    )
    result = get_trust_center_asset(_session, "tenant-p11-01", asset["id"])
    assert result is None


def test_get_asset_blocks_above_sensitivity(_session) -> None:
    """P1 Fix: get_trust_center_asset returns None when sensitivity exceeds ceiling."""
    from app.services.trust_center_service import (
        create_trust_center_asset,
        get_trust_center_asset,
    )

    asset = create_trust_center_asset(
        _session,
        "tenant-p11-02",
        {"title": "Internal Only", "sensitivity": "internal", "published": True},
    )
    # Viewer ceiling (prospect) should NOT see internal docs
    result = get_trust_center_asset(
        _session, "tenant-p11-02", asset["id"], sensitivity_max="prospect"
    )
    assert result is None

    # Admin ceiling (internal) should see it
    result_ok = get_trust_center_asset(
        _session, "tenant-p11-02", asset["id"], sensitivity_max="internal"
    )
    assert result_ok is not None
    assert result_ok["title"] == "Internal Only"


def test_get_asset_sensitivity_boundary(_session) -> None:
    """P1 Fix: exact boundary – auditor ceiling can see auditor but not internal."""
    from app.services.trust_center_service import (
        create_trust_center_asset,
        get_trust_center_asset,
    )

    auditor_doc = create_trust_center_asset(
        _session,
        "tenant-p11-03",
        {"title": "Auditor Doc", "sensitivity": "auditor", "published": True},
    )
    internal_doc = create_trust_center_asset(
        _session,
        "tenant-p11-03",
        {"title": "Internal Doc", "sensitivity": "internal", "published": True},
    )
    # auditor ceiling: can see auditor doc
    assert (
        get_trust_center_asset(
            _session, "tenant-p11-03", auditor_doc["id"], sensitivity_max="auditor"
        )
        is not None
    )
    # auditor ceiling: cannot see internal doc
    assert (
        get_trust_center_asset(
            _session, "tenant-p11-03", internal_doc["id"], sensitivity_max="auditor"
        )
        is None
    )


def test_compliance_mapping_sensitivity_ceiling(_session) -> None:
    """P1 Fix: compliance mapping respects sensitivity ceiling."""
    from app.services.trust_center_service import (
        create_trust_center_asset,
        get_compliance_mapping_overview,
    )

    create_trust_center_asset(
        _session,
        "tenant-p11-04",
        {
            "title": "Public Control",
            "sensitivity": "public",
            "framework_refs": ["ISO_27001"],
            "published": True,
        },
    )
    create_trust_center_asset(
        _session,
        "tenant-p11-04",
        {
            "title": "Internal Control",
            "sensitivity": "internal",
            "framework_refs": ["ISO_27001", "NIS2"],
            "published": True,
        },
    )

    # Viewer (prospect ceiling) → sees only 1 control
    viewer_map = get_compliance_mapping_overview(
        _session, "tenant-p11-04", sensitivity_max="prospect"
    )
    assert viewer_map["total_controls"] == 1

    # Admin (internal ceiling) → sees both
    admin_map = get_compliance_mapping_overview(
        _session, "tenant-p11-04", sensitivity_max="internal"
    )
    assert admin_map["total_controls"] == 2


def test_compliance_mapping_viewer_no_auditor_assets(_session) -> None:
    """Viewer must not see AUDITOR_ONLY or INTERNAL assets in compliance mapping."""
    from app.services.trust_center_service import (
        create_trust_center_asset,
        get_compliance_mapping_overview,
    )

    create_trust_center_asset(
        _session,
        "tenant-p11-05",
        {
            "title": "Customer Doc",
            "sensitivity": "customer",
            "framework_refs": ["DSGVO"],
            "published": True,
        },
    )
    create_trust_center_asset(
        _session,
        "tenant-p11-05",
        {
            "title": "Auditor-Only Doc",
            "sensitivity": "auditor",
            "framework_refs": ["DSGVO"],
            "published": True,
        },
    )

    viewer_map = get_compliance_mapping_overview(
        _session, "tenant-p11-05", sensitivity_max="prospect"
    )
    assert viewer_map["total_controls"] == 0  # prospect can't even see customer

    customer_map = get_compliance_mapping_overview(
        _session, "tenant-p11-05", sensitivity_max="customer"
    )
    assert customer_map["total_controls"] == 1
    assert customer_map["controls"][0]["title"] == "Customer Doc"


def test_sign_and_verify_evidence_bundle(_session) -> None:
    """E-Signing: sign + verify with cryptographic validation."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    from app.services.trust_center_service import (
        _get_signing_key_pem,
        generate_evidence_bundle,
        sign_evidence_bundle,
        verify_evidence_bundle,
    )

    bundle = generate_evidence_bundle(_session, "tenant-p11-06", "iso_27001")
    assert bundle["signature"] is None

    signed = sign_evidence_bundle(_session, "tenant-p11-06", bundle["id"], "compliance_admin")
    assert signed is not None
    assert signed["signature"] is not None
    assert signed["cert_fingerprint"] is not None
    assert signed["signed_at"] is not None
    assert signed["signed_by_role"] == "compliance_admin"
    assert signed["signing_key_id"] is not None

    # Verify via service (cryptographic check)
    result = verify_evidence_bundle(_session, "tenant-p11-06", bundle["id"])
    assert result is not None
    assert result["valid"] is True
    assert result["signer_role"] == "compliance_admin"
    assert result["key_id"] is not None
    assert result["payload_binding"] == "verified"
    assert result["long_term_valid"] is True

    # Also verify the signature directly with the crypto library
    key_pem = _get_signing_key_pem()
    private_key = serialization.load_pem_private_key(key_pem, password=None)
    assert isinstance(private_key, ec.EllipticCurvePrivateKey)
    public_key = private_key.public_key()
    sig_bytes = bytes.fromhex(signed["signature"])
    payload = signed["metadata"]["signed_payload"].encode()
    # This will raise if the signature is invalid
    public_key.verify(sig_bytes, payload, ec.ECDSA(hashes.SHA256()))


def test_verify_unsigned_bundle(_session) -> None:
    """E-Signing: verify returns valid=False for unsigned bundles."""
    from app.services.trust_center_service import (
        generate_evidence_bundle,
        verify_evidence_bundle,
    )

    bundle = generate_evidence_bundle(_session, "tenant-p11-07", "dsgvo")

    result = verify_evidence_bundle(_session, "tenant-p11-07", bundle["id"])
    assert result is not None
    assert result["valid"] is False


def test_role_sensitivity_mapping() -> None:
    """Role sensitivity helper returns correct ceilings."""
    from app.services.trust_center_service import max_sensitivity_for_role

    assert max_sensitivity_for_role("viewer") == "prospect"
    assert max_sensitivity_for_role("contributor") == "customer"
    assert max_sensitivity_for_role("auditor") == "auditor"
    assert max_sensitivity_for_role("compliance_admin") == "internal"
    assert max_sensitivity_for_role("tenant_admin") == "internal"
    assert max_sensitivity_for_role("unknown_role") == "customer"


def test_migration_phase11_satisfied(_engine) -> None:
    """Phase 11 migration is satisfied after create_all."""
    from app.db_migrations.migrations.m20260420_phase11_trust_center_esigning import (
        satisfied,
    )

    assert satisfied(_engine)


def test_migration_phase11_apply_idempotent(_engine) -> None:
    from app.db_migrations.migrations.m20260420_phase11_trust_center_esigning import (
        apply,
    )

    assert apply(_engine) is False


# ---------------------------------------------------------------------------
# Phase 12 – Key-Rotation-Safe Verification & Payload-Binding Tests
# ---------------------------------------------------------------------------


def test_key_rotation_verification(_session) -> None:
    """Key rotation: bundle signed with v1 key remains valid after registry switch to v2."""
    import json

    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

    from app.services.trust_center_service import (
        generate_evidence_bundle,
        sign_evidence_bundle,
        verify_evidence_bundle,
    )

    # Sign a bundle with the default dev key (kid=v1)
    bundle = generate_evidence_bundle(_session, "tenant-p12-kr", "iso_27001")
    signed = sign_evidence_bundle(_session, "tenant-p12-kr", bundle["id"], "tenant_admin")
    assert signed is not None
    assert signed["signing_key_id"] == "v1"

    # Generate a second key (v2)
    v2_key = ec.generate_private_key(ec.SECP256R1())
    v2_pem = v2_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode()

    # Get v1 key PEM for registry
    from app.services.trust_center_service import _get_signing_key_pem

    v1_pem = _get_signing_key_pem().decode()

    # Set TRUST_CENTER_SIGNING_KEYS with both keys, v2 active
    import os

    keys_json = json.dumps(
        [
            {"kid": "v1", "key_pem": v1_pem, "active": False},
            {"kid": "v2", "key_pem": v2_pem, "active": True},
        ]
    )
    os.environ["TRUST_CENTER_SIGNING_KEYS"] = keys_json
    try:
        # Verify the v1-signed bundle — must still be valid
        result = verify_evidence_bundle(_session, "tenant-p12-kr", bundle["id"])
        assert result is not None
        assert result["valid"] is True
        assert result["key_id"] == "v1"
        assert result["payload_binding"] == "verified"
        assert result["long_term_valid"] is True
    finally:
        os.environ.pop("TRUST_CENTER_SIGNING_KEYS", None)


def test_payload_transplant_attack(_session) -> None:
    """Payload transplant: copying signature+payload to another bundle is detected."""
    from app.models_db import EvidenceBundleDB
    from app.services.trust_center_service import (
        generate_evidence_bundle,
        sign_evidence_bundle,
        verify_evidence_bundle,
    )

    # Create and sign bundle A
    bundle_a = generate_evidence_bundle(_session, "tenant-p12-pt", "iso_27001")
    signed_a = sign_evidence_bundle(_session, "tenant-p12-pt", bundle_a["id"], "compliance_admin")
    assert signed_a is not None

    # Create bundle B (unsigned)
    bundle_b = generate_evidence_bundle(_session, "tenant-p12-pt", "dsgvo")

    # Transplant signature + payload from A into B
    row_b = _session.query(EvidenceBundleDB).filter(EvidenceBundleDB.id == bundle_b["id"]).first()
    row_a = _session.query(EvidenceBundleDB).filter(EvidenceBundleDB.id == bundle_a["id"]).first()
    row_b.signature = row_a.signature
    row_b.cert_fingerprint = row_a.cert_fingerprint
    row_b.signed_at = row_a.signed_at
    row_b.signed_by_role = row_a.signed_by_role
    row_b.signing_key_id = row_a.signing_key_id
    row_b.signed_payload = row_a.signed_payload
    row_b.metadata_payload = dict(row_a.metadata_payload or {})
    _session.commit()

    # Verify bundle B — must detect payload-binding violation
    result = verify_evidence_bundle(_session, "tenant-p12-pt", bundle_b["id"])
    assert result is not None
    assert result["valid"] is False
    assert result["payload_binding"] == "violation"
    assert "Payload-Binding-Verletzung" in result.get("reason", "")


def test_unknown_kid_verification(_session) -> None:
    """Bundle with unknown kid: verification returns valid=False with reason."""
    from app.models_db import EvidenceBundleDB
    from app.services.trust_center_service import (
        generate_evidence_bundle,
        sign_evidence_bundle,
        verify_evidence_bundle,
    )

    # Create and sign a bundle
    bundle = generate_evidence_bundle(_session, "tenant-p12-uk", "iso_27001")
    signed = sign_evidence_bundle(_session, "tenant-p12-uk", bundle["id"], "tenant_admin")
    assert signed is not None

    # Tamper: set an unknown kid
    row = _session.query(EvidenceBundleDB).filter(EvidenceBundleDB.id == bundle["id"]).first()
    row.signing_key_id = "v999_unknown"
    _session.commit()

    result = verify_evidence_bundle(_session, "tenant-p12-uk", bundle["id"])
    assert result is not None
    assert result["valid"] is False
    assert result["key_id"] == "v999_unknown"
    assert "nicht mehr verfügbar" in result.get("reason", "")


def test_backward_compat_phase11_bundle(_session) -> None:
    """Phase 11 bundles without kid/signed_payload columns are still verifiable."""
    from app.models_db import EvidenceBundleDB
    from app.services.trust_center_service import (
        generate_evidence_bundle,
        sign_evidence_bundle,
        verify_evidence_bundle,
    )

    # Create and sign a bundle normally (Phase 12 style)
    bundle = generate_evidence_bundle(_session, "tenant-p12-bc", "dsgvo")
    signed = sign_evidence_bundle(_session, "tenant-p12-bc", bundle["id"], "compliance_admin")
    assert signed is not None

    # Simulate a Phase 11 bundle: clear the Phase 12 columns
    row = _session.query(EvidenceBundleDB).filter(EvidenceBundleDB.id == bundle["id"]).first()
    row.signing_key_id = None  # Phase 11 didn't have this
    row.signed_payload = None  # Phase 11 didn't have this
    _session.commit()

    # Verify — should fall back to kid=v1 from metadata and payload from metadata
    result = verify_evidence_bundle(_session, "tenant-p12-bc", bundle["id"])
    assert result is not None
    assert result["valid"] is True
    assert result["key_id"] == "v1"
    assert result["payload_binding"] == "verified"
    assert result["long_term_valid"] is True


def test_migration_phase12_satisfied(_engine) -> None:
    """Phase 12 migration is satisfied after create_all."""
    from app.db_migrations.migrations.m20260421_phase12_esigning_key_rotation import (
        satisfied,
    )

    assert satisfied(_engine)


def test_migration_phase12_apply_idempotent(_engine) -> None:
    from app.db_migrations.migrations.m20260421_phase12_esigning_key_rotation import (
        apply,
    )

    assert apply(_engine) is False


# ---------------------------------------------------------------------------
# Phase 13 – Fingerprint-based Legacy Lookup & Empty-Registry Guard Tests
# ---------------------------------------------------------------------------


def test_legacy_fingerprint_lookup(_session) -> None:
    """Legacy bundle without signing_key_id resolves via fingerprint match under custom kid."""
    import json
    import os

    from app.models_db import EvidenceBundleDB
    from app.services.trust_center_service import (
        _get_signing_key_pem,
        generate_evidence_bundle,
        sign_evidence_bundle,
        verify_evidence_bundle,
    )

    # Sign a bundle normally (kid=v1)
    bundle = generate_evidence_bundle(_session, "tenant-p13-fp", "iso_27001")
    signed = sign_evidence_bundle(_session, "tenant-p13-fp", bundle["id"], "compliance_admin")
    assert signed is not None
    assert signed["signing_key_id"] == "v1"

    # Simulate Phase-11 legacy bundle: clear signing_key_id but keep cert_fingerprint
    row = _session.query(EvidenceBundleDB).filter(EvidenceBundleDB.id == bundle["id"]).first()
    row.signing_key_id = None
    row.signed_payload = None  # Phase-11 didn't have this
    # Clear kid from metadata to force fingerprint-based resolution
    meta = dict(row.metadata_payload or {})
    meta.pop("kid", None)
    row.metadata_payload = meta
    _session.commit()

    # Now register the same key under a custom kid ("prod-2026-04")
    v1_pem = _get_signing_key_pem().decode()
    keys_json = json.dumps([{"kid": "prod-2026-04", "key_pem": v1_pem, "active": True}])
    os.environ["TRUST_CENTER_SIGNING_KEYS"] = keys_json
    try:
        result = verify_evidence_bundle(_session, "tenant-p13-fp", bundle["id"])
        assert result is not None
        assert result["valid"] is True
        assert result["key_id"] == "prod-2026-04"
        assert result["legacy_lookup_method"] == "fingerprint"
        assert result["payload_binding"] == "verified"
        assert result["long_term_valid"] is True
    finally:
        os.environ.pop("TRUST_CENTER_SIGNING_KEYS", None)


def test_empty_registry_503(_session) -> None:
    """Empty key registry raises KeyRegistryError → 503 on sign."""
    import json
    import os

    from app.services.trust_center_service import (
        KeyRegistryError,
        _get_active_signing_key,
    )

    keys_json = json.dumps([])
    os.environ["TRUST_CENTER_SIGNING_KEYS"] = keys_json
    try:
        try:
            _get_active_signing_key()
            raised = False
        except KeyRegistryError as exc:
            raised = True
            assert "leer" in str(exc).lower() or "TRUST_CENTER_SIGNING_KEYS" in str(exc)
        assert raised, "_get_active_signing_key should raise KeyRegistryError for empty registry"
    finally:
        os.environ.pop("TRUST_CENTER_SIGNING_KEYS", None)


def test_migration_phase13_satisfied(_engine) -> None:
    """Phase 13 migration is satisfied after create_all."""
    from app.db_migrations.migrations.m20260422_phase13_tenant_onboarding_completed import (
        satisfied,
    )

    assert satisfied(_engine)


def test_migration_phase13_apply_idempotent(_engine) -> None:
    from app.db_migrations.migrations.m20260422_phase13_tenant_onboarding_completed import (
        apply,
    )

    assert apply(_engine) is False
