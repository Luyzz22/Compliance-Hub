"""Trust Center & Assurance Portal service layer.

Handles asset management, evidence bundle generation, compliance mapping,
and access logging for the enterprise Trust Center.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models_db import (
    EvidenceBundleDB,
    TrustCenterAccessLogDB,
    TrustCenterAssetDB,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ASSET_TYPES = (
    "policy",
    "certificate",
    "audit_report",
    "tom",
    "compliance_snapshot",
    "board_pdf",
)

SENSITIVITY_LEVELS = ("public", "prospect", "customer", "auditor", "internal")

# ---------------------------------------------------------------------------
# Role → maximum sensitivity mapping
# ---------------------------------------------------------------------------

ROLE_SENSITIVITY_MAP: dict[str, str] = {
    "viewer": "prospect",
    "contributor": "customer",
    "editor": "customer",
    "auditor": "auditor",
    "compliance_officer": "internal",
    "ciso": "internal",
    "board_member": "customer",
    "compliance_admin": "internal",
    "tenant_admin": "internal",
    "super_admin": "internal",
}


def max_sensitivity_for_role(role: str) -> str:
    """Return the highest sensitivity level a role may access."""
    return ROLE_SENSITIVITY_MAP.get(role, "customer")


def _sensitivity_allowed(asset_sensitivity: str, ceiling: str) -> bool:
    """Return True if *asset_sensitivity* is at or below *ceiling*."""
    try:
        return SENSITIVITY_LEVELS.index(asset_sensitivity) <= SENSITIVITY_LEVELS.index(ceiling)
    except ValueError:
        return False


BUNDLE_TYPES = (
    "iso_27001",
    "nis2",
    "dsgvo",
    "eu_ai_act",
    "gobd_revision",
    "vendor_security_review",
    "auditor_bundle",
)

COMPLIANCE_FRAMEWORKS = (
    "EU_AI_ACT",
    "ISO_42001",
    "ISO_27001",
    "NIS2",
    "DSGVO",
    "GoBD",
)

# Bundle type → default title and description (DE)
_BUNDLE_DEFAULTS: dict[str, dict[str, str]] = {
    "iso_27001": {
        "title": "ISO 27001 Evidence Bundle",
        "description": (
            "ISMS-Policies, Kontroll-Mappings, Audit-Log-Exporte und Risikozusammenfassungen."
        ),
    },
    "nis2": {
        "title": "NIS2 Compliance Bundle",
        "description": "NIS2-Pflicht-Mappings, Incident-Zusammenfassungen und Kontrollnachweise.",
    },
    "dsgvo": {
        "title": "DSGVO / GDPR Evidence Bundle",
        "description": "Verarbeitungsverzeichnis, TOM-Dokumentation und AVV-Nachweise.",
    },
    "eu_ai_act": {
        "title": "EU AI Act Evidence Bundle",
        "description": "KI-Register, Risikoklassifikationen und Human-Oversight-Nachweise.",
    },
    "gobd_revision": {
        "title": "GoBD / Revision Evidence Bundle",
        "description": "GoBD-Compliance-Nachweise, DATEV-Exporte und Audit-Trails.",
    },
    "vendor_security_review": {
        "title": "Vendor Security Review Bundle",
        "description": "Sicherheitsüberblick, Architektur und Kontrollzusammenfassung.",
    },
    "auditor_bundle": {
        "title": "Auditor Full Evidence Bundle",
        "description": "Vollständiges Audit-Evidenzpaket über alle Frameworks.",
    },
}


# ---------------------------------------------------------------------------
# Access Logging
# ---------------------------------------------------------------------------


def log_trust_center_access(
    session: Session,
    *,
    tenant_id: str,
    actor: str | None = None,
    role: str | None = None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    ip_address: str | None = None,
    metadata_json: str | None = None,
) -> None:
    """Write an immutable access-log entry for trust center interactions."""
    entry = TrustCenterAccessLogDB(
        tenant_id=tenant_id,
        actor=actor,
        role=role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        metadata_json=metadata_json,
        created_at_utc=datetime.now(UTC),
    )
    session.add(entry)
    session.commit()


# ---------------------------------------------------------------------------
# Trust Center Assets
# ---------------------------------------------------------------------------


def list_trust_center_assets(
    session: Session,
    tenant_id: str,
    *,
    sensitivity_max: str = "internal",
    published_only: bool = True,
) -> list[dict[str, Any]]:
    """List assets visible at the given sensitivity ceiling."""
    allowed = list(SENSITIVITY_LEVELS[: SENSITIVITY_LEVELS.index(sensitivity_max) + 1])
    query = session.query(TrustCenterAssetDB).filter(
        TrustCenterAssetDB.tenant_id == tenant_id,
        TrustCenterAssetDB.sensitivity.in_(allowed),
    )
    if published_only:
        query = query.filter(TrustCenterAssetDB.published.is_(True))
    query = query.order_by(TrustCenterAssetDB.created_at_utc.desc())
    return [_asset_to_dict(a) for a in query.all()]


def get_trust_center_asset(
    session: Session,
    tenant_id: str,
    asset_id: str,
    *,
    sensitivity_max: str = "internal",
) -> dict[str, Any] | None:
    """Retrieve a single asset by ID (tenant-scoped, sensitivity-gated).

    Returns ``None`` (→ 404) when the asset is unpublished or exceeds the
    caller's sensitivity ceiling.  This avoids leaking asset existence.
    """
    row = (
        session.query(TrustCenterAssetDB)
        .filter(
            TrustCenterAssetDB.id == asset_id,
            TrustCenterAssetDB.tenant_id == tenant_id,
            TrustCenterAssetDB.published.is_(True),
        )
        .first()
    )
    if not row:
        return None
    if not _sensitivity_allowed(row.sensitivity, sensitivity_max):
        return None
    return _asset_to_dict(row)


def create_trust_center_asset(
    session: Session, tenant_id: str, data: dict[str, Any]
) -> dict[str, Any]:
    """Create a new trust center asset."""
    now = datetime.now(UTC)
    asset = TrustCenterAssetDB(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        title=data["title"],
        description=data.get("description"),
        asset_type=data.get("asset_type", "policy"),
        sensitivity=data.get("sensitivity", "customer"),
        framework_refs=data.get("framework_refs", []),
        file_name=data.get("file_name"),
        published=data.get("published", False),
        valid_from=data.get("valid_from"),
        valid_until=data.get("valid_until"),
        review_date=data.get("review_date"),
        created_at_utc=now,
        updated_at_utc=now,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return _asset_to_dict(asset)


def update_trust_center_asset(
    session: Session, tenant_id: str, asset_id: str, data: dict[str, Any]
) -> dict[str, Any] | None:
    """Update an existing trust center asset."""
    row = (
        session.query(TrustCenterAssetDB)
        .filter(
            TrustCenterAssetDB.id == asset_id,
            TrustCenterAssetDB.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        return None
    for field in (
        "title",
        "description",
        "asset_type",
        "sensitivity",
        "framework_refs",
        "file_name",
        "published",
        "valid_from",
        "valid_until",
        "review_date",
    ):
        if field in data:
            setattr(row, field, data[field])
    row.updated_at_utc = datetime.now(UTC)
    session.commit()
    session.refresh(row)
    return _asset_to_dict(row)


def _asset_to_dict(row: TrustCenterAssetDB) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "title": row.title,
        "description": row.description,
        "asset_type": row.asset_type,
        "sensitivity": row.sensitivity,
        "framework_refs": row.framework_refs,
        "file_name": row.file_name,
        "published": row.published,
        "valid_from": row.valid_from.isoformat() if row.valid_from else None,
        "valid_until": row.valid_until.isoformat() if row.valid_until else None,
        "review_date": row.review_date.isoformat() if row.review_date else None,
        "created_at_utc": row.created_at_utc.isoformat() if row.created_at_utc else None,
        "updated_at_utc": row.updated_at_utc.isoformat() if row.updated_at_utc else None,
    }


# ---------------------------------------------------------------------------
# Evidence Bundles
# ---------------------------------------------------------------------------


def list_evidence_bundles(session: Session, tenant_id: str) -> list[dict[str, Any]]:
    """List all evidence bundles for a tenant."""
    rows = (
        session.query(EvidenceBundleDB)
        .filter(EvidenceBundleDB.tenant_id == tenant_id)
        .order_by(EvidenceBundleDB.created_at_utc.desc())
        .all()
    )
    return [_bundle_to_dict(r) for r in rows]


def get_evidence_bundle(session: Session, tenant_id: str, bundle_id: str) -> dict[str, Any] | None:
    """Retrieve a single evidence bundle by ID (tenant-scoped)."""
    row = (
        session.query(EvidenceBundleDB)
        .filter(
            EvidenceBundleDB.id == bundle_id,
            EvidenceBundleDB.tenant_id == tenant_id,
        )
        .first()
    )
    return _bundle_to_dict(row) if row else None


def generate_evidence_bundle(
    session: Session,
    tenant_id: str,
    bundle_type: str,
) -> dict[str, Any]:
    """Generate a new evidence bundle of the given type.

    In production this would pull real artefacts; here we scaffold the
    metadata record and reference relevant existing trust-center assets.
    """
    defaults = _BUNDLE_DEFAULTS.get(bundle_type, {})
    now = datetime.now(UTC)

    # Collect asset IDs that match the bundle's frameworks
    framework_filter = _bundle_framework_filter(bundle_type)
    assets = (
        session.query(TrustCenterAssetDB)
        .filter(
            TrustCenterAssetDB.tenant_id == tenant_id,
            TrustCenterAssetDB.published.is_(True),
        )
        .all()
    )
    artefact_ids = [
        a.id
        for a in assets
        if not framework_filter or any(f in (a.framework_refs or []) for f in framework_filter)
    ]

    bundle = EvidenceBundleDB(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        bundle_type=bundle_type,
        title=defaults.get("title", f"Evidence Bundle ({bundle_type})"),
        description=defaults.get("description"),
        artefact_ids=artefact_ids,
        metadata_payload={
            "created_at": now.isoformat(),
            "validity_date": now.isoformat(),
            "tenant_id": tenant_id,
            "scope": bundle_type,
            "sensitivity": "auditor",
            "frameworks": framework_filter,
        },
        sensitivity="auditor",
        created_at_utc=now,
    )
    session.add(bundle)
    session.commit()
    session.refresh(bundle)
    return _bundle_to_dict(bundle)


def _bundle_framework_filter(bundle_type: str) -> list[str]:
    mapping: dict[str, list[str]] = {
        "iso_27001": ["ISO_27001"],
        "nis2": ["NIS2"],
        "dsgvo": ["DSGVO"],
        "eu_ai_act": ["EU_AI_ACT", "ISO_42001"],
        "gobd_revision": ["GoBD"],
        "vendor_security_review": ["ISO_27001", "NIS2"],
        "auditor_bundle": [],  # all frameworks
    }
    return mapping.get(bundle_type, [])


def _bundle_to_dict(row: EvidenceBundleDB) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "bundle_type": row.bundle_type,
        "title": row.title,
        "description": row.description,
        "artefact_ids": row.artefact_ids,
        "metadata": row.metadata_payload,
        "sensitivity": row.sensitivity,
        "created_at_utc": row.created_at_utc.isoformat() if row.created_at_utc else None,
        "signature": row.signature if hasattr(row, "signature") else None,
        "cert_fingerprint": row.cert_fingerprint if hasattr(row, "cert_fingerprint") else None,
        "signed_at": (
            row.signed_at.isoformat() if hasattr(row, "signed_at") and row.signed_at else None
        ),
        "signed_by_role": row.signed_by_role if hasattr(row, "signed_by_role") else None,
    }


# ---------------------------------------------------------------------------
# Evidence Bundle E-Signing (ECDSA-P256 / eIDAS / GoBD)
# ---------------------------------------------------------------------------


def _get_signing_key_pem() -> bytes:
    """Load the PEM-encoded ECDSA private key from env var.

    Falls back to a deterministic dev key when the env var
    ``TRUST_CENTER_SIGNING_KEY`` is absent.  **Not for production use.**
    """
    import logging

    raw = os.environ.get("TRUST_CENTER_SIGNING_KEY")
    if raw:
        return raw.encode()

    logger = logging.getLogger(__name__)
    logger.warning(
        "TRUST_CENTER_SIGNING_KEY not set – using deterministic dev key. Do NOT use in production."
    )

    # Deterministic dev fallback: derive a fixed key from a static seed.
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

    seed = hashlib.sha256(b"compliance-hub-dev-signing-key-seed").digest()
    # Use the full 256-bit seed as private value (valid for SECP256R1 order ~ 2^256)
    private_value = int.from_bytes(seed, "big")
    # Clamp to valid range [1, curve_order - 1]
    curve_order = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
    private_value = (private_value % (curve_order - 1)) + 1
    dev_key = ec.derive_private_key(private_value, ec.SECP256R1())
    return dev_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())


def sign_evidence_bundle(
    session: Session,
    tenant_id: str,
    bundle_id: str,
    signer_role: str,
) -> dict[str, Any] | None:
    """Sign an evidence bundle with ECDSA-P256.

    Stores the DER-hex signature, cert fingerprint, timestamp, and
    signer role on the bundle row.  Returns the updated bundle dict or
    ``None`` when the bundle is not found.
    """
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    row = (
        session.query(EvidenceBundleDB)
        .filter(
            EvidenceBundleDB.id == bundle_id,
            EvidenceBundleDB.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        return None

    # Build canonical payload to sign
    now = datetime.now(UTC)
    payload = f"{row.id}|{row.tenant_id}|{now.isoformat()}".encode()

    key_pem = _get_signing_key_pem()
    private_key = serialization.load_pem_private_key(key_pem, password=None)
    assert isinstance(private_key, ec.EllipticCurvePrivateKey)

    sig_bytes = private_key.sign(payload, ec.ECDSA(hashes.SHA256()))

    # Compute fingerprint of the public key (SHA-256 of DER)
    pub_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    fingerprint = hashlib.sha256(pub_der).hexdigest()

    row.signature = sig_bytes.hex()
    row.cert_fingerprint = fingerprint
    row.signed_at = now
    row.signed_by_role = signer_role
    # Store the signed payload so verification can reconstruct it
    meta = dict(row.metadata_payload or {})
    meta["signed_payload"] = payload.decode()
    row.metadata_payload = meta
    session.commit()
    session.refresh(row)
    return _bundle_to_dict(row)


def verify_evidence_bundle(
    session: Session,
    tenant_id: str,
    bundle_id: str,
) -> dict[str, Any] | None:
    """Verify the cryptographic signature of an evidence bundle.

    Reconstructs the signed payload and verifies the ECDSA signature
    against the signing public key.  Returns a dict with ``valid``,
    ``signed_at``, and ``signer_role`` or ``None`` when the bundle
    does not exist.
    """
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    row = (
        session.query(EvidenceBundleDB)
        .filter(
            EvidenceBundleDB.id == bundle_id,
            EvidenceBundleDB.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        return None

    if not getattr(row, "signature", None):
        return {
            "valid": False,
            "signed_at": None,
            "signer_role": None,
            "reason": "Bundle ist nicht signiert.",
        }

    # Retrieve the signed payload stored during signing
    meta = row.metadata_payload or {}
    signed_payload_str = meta.get("signed_payload")
    if not signed_payload_str:
        return {
            "valid": False,
            "signed_at": row.signed_at.isoformat() if row.signed_at else None,
            "signer_role": row.signed_by_role,
            "reason": "Signierter Payload fehlt – Signatur nicht verifizierbar.",
        }

    try:
        key_pem = _get_signing_key_pem()
        private_key = serialization.load_pem_private_key(key_pem, password=None)
        assert isinstance(private_key, ec.EllipticCurvePrivateKey)
        public_key = private_key.public_key()

        sig_bytes = bytes.fromhex(row.signature)
        payload = signed_payload_str.encode()
        public_key.verify(sig_bytes, payload, ec.ECDSA(hashes.SHA256()))

        return {
            "valid": True,
            "signed_at": row.signed_at.isoformat() if row.signed_at else None,
            "signer_role": row.signed_by_role,
        }
    except Exception:
        return {
            "valid": False,
            "signed_at": row.signed_at.isoformat() if row.signed_at else None,
            "signer_role": row.signed_by_role,
            "reason": "Signaturprüfung fehlgeschlagen – Integrität nicht bestätigt.",
        }


# ---------------------------------------------------------------------------
# Compliance Mapping Overview
# ---------------------------------------------------------------------------


def get_compliance_mapping_overview(
    session: Session,
    tenant_id: str,
    *,
    sensitivity_max: str = "internal",
) -> dict[str, Any]:
    """Build a high-level compliance mapping view.

    Returns a matrix of controls (trust center assets of type 'tom')
    mapped against the six core DACH frameworks, plus coverage statistics.
    Assets above the caller's sensitivity ceiling are excluded.
    """
    allowed = list(SENSITIVITY_LEVELS[: SENSITIVITY_LEVELS.index(sensitivity_max) + 1])
    assets = (
        session.query(TrustCenterAssetDB)
        .filter(
            TrustCenterAssetDB.tenant_id == tenant_id,
            TrustCenterAssetDB.published.is_(True),
            TrustCenterAssetDB.sensitivity.in_(allowed),
        )
        .all()
    )

    framework_counts: dict[str, int] = {fw: 0 for fw in COMPLIANCE_FRAMEWORKS}
    controls: list[dict[str, Any]] = []

    for asset in assets:
        refs = asset.framework_refs or []
        coverage: dict[str, str] = {}
        for fw in COMPLIANCE_FRAMEWORKS:
            if fw in refs:
                coverage[fw] = "full"
                framework_counts[fw] += 1
            else:
                coverage[fw] = "not_applicable"
        controls.append(
            {
                "id": asset.id,
                "title": asset.title,
                "asset_type": asset.asset_type,
                "coverage": coverage,
            }
        )

    total = len(assets) or 1
    framework_coverage = {fw: round(count / total, 2) for fw, count in framework_counts.items()}

    return {
        "tenant_id": tenant_id,
        "frameworks": list(COMPLIANCE_FRAMEWORKS),
        "controls": controls,
        "framework_coverage": framework_coverage,
        "total_controls": len(assets),
    }


# ---------------------------------------------------------------------------
# Trust Center Public Content
# ---------------------------------------------------------------------------


def get_public_trust_center_content() -> dict[str, Any]:
    """Static public trust center content derived from system capabilities."""
    return {
        "security_overview": {
            "title": "Sicherheitsarchitektur",
            "description": (
                "Enterprise-grade Sicherheitsarchitektur mit Verschlüsselung, "
                "RBAC, Audit-Trails und Tenant-Isolation."
            ),
            "commitments": [
                "Verschlüsselung in Transit und at Rest",
                "Rollenbasierte Zugriffskontrolle (RBAC)",
                "Immutable Audit-Log für alle Änderungen",
                "Multi-Faktor-Authentifizierung (MFA)",
                "Separation of Duties (SoD) Policies",
            ],
        },
        "compliance_overview": {
            "title": "Compliance-Status",
            "frameworks": [
                {"key": "EU_AI_ACT", "label": "EU AI Act", "status": "active"},
                {"key": "ISO_42001", "label": "ISO 42001", "status": "active"},
                {"key": "ISO_27001", "label": "ISO 27001", "status": "active"},
                {"key": "NIS2", "label": "NIS2", "status": "active"},
                {"key": "DSGVO", "label": "DSGVO", "status": "active"},
                {"key": "GoBD", "label": "GoBD", "status": "active"},
            ],
        },
        "data_residency": {
            "title": "Datenresidenz & Hosting",
            "description": (
                "Primärer Betrieb in EU-Regionen mit klaren Residency-Policies "
                "für DACH-Kunden, inklusive Mandanten-Region-Pinning."
            ),
            "hosting_region": "EU (Frankfurt / DACH)",
            "certifications": ["ISO 27001", "SOC 2 Type II"],
        },
        "subprocessors": {
            "title": "Subprocessor-Transparenz",
            "description": "Vollständige Transparenz über eingesetzte Unterauftragsverarbeiter.",
            "last_updated": "2026-04-01",
        },
        "responsible_disclosure": {
            "title": "Responsible Disclosure",
            "contact": "security@compliancehub.de",
            "pgp_available": True,
        },
    }
