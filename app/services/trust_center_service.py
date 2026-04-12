"""Trust Center & Assurance Portal service layer.

Handles asset management, evidence bundle generation, compliance mapping,
and access logging for the enterprise Trust Center.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
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
        "description": "ISMS-Policies, Kontroll-Mappings, Audit-Log-Exporte und Risikozusammenfassungen.",
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
        created_at_utc=datetime.now(timezone.utc),
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
    session: Session, tenant_id: str, asset_id: str
) -> dict[str, Any] | None:
    """Retrieve a single asset by ID (tenant-scoped)."""
    row = (
        session.query(TrustCenterAssetDB)
        .filter(
            TrustCenterAssetDB.id == asset_id,
            TrustCenterAssetDB.tenant_id == tenant_id,
        )
        .first()
    )
    return _asset_to_dict(row) if row else None


def create_trust_center_asset(
    session: Session, tenant_id: str, data: dict[str, Any]
) -> dict[str, Any]:
    """Create a new trust center asset."""
    now = datetime.now(timezone.utc)
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
    row.updated_at_utc = datetime.now(timezone.utc)
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


def list_evidence_bundles(
    session: Session, tenant_id: str
) -> list[dict[str, Any]]:
    """List all evidence bundles for a tenant."""
    rows = (
        session.query(EvidenceBundleDB)
        .filter(EvidenceBundleDB.tenant_id == tenant_id)
        .order_by(EvidenceBundleDB.created_at_utc.desc())
        .all()
    )
    return [_bundle_to_dict(r) for r in rows]


def get_evidence_bundle(
    session: Session, tenant_id: str, bundle_id: str
) -> dict[str, Any] | None:
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
    now = datetime.now(timezone.utc)

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
        if not framework_filter
        or any(f in (a.framework_refs or []) for f in framework_filter)
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
    }


# ---------------------------------------------------------------------------
# Compliance Mapping Overview
# ---------------------------------------------------------------------------


def get_compliance_mapping_overview(
    session: Session, tenant_id: str
) -> dict[str, Any]:
    """Build a high-level compliance mapping view.

    Returns a matrix of controls (trust center assets of type 'tom')
    mapped against the six core DACH frameworks, plus coverage statistics.
    """
    assets = (
        session.query(TrustCenterAssetDB)
        .filter(
            TrustCenterAssetDB.tenant_id == tenant_id,
            TrustCenterAssetDB.published.is_(True),
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
    framework_coverage = {
        fw: round(count / total, 2) for fw, count in framework_counts.items()
    }

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
