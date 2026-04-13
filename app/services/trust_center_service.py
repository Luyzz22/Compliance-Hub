"""Trust Center & Assurance Portal service layer.

Handles asset management, evidence bundle generation, compliance mapping,
and access logging for the enterprise Trust Center.
"""

from __future__ import annotations

import hashlib
import logging
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
        "signing_key_id": getattr(row, "signing_key_id", None),
        "signed_payload": getattr(row, "signed_payload", None),
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


class KeyRegistryError(Exception):
    """Raised when the key registry is empty or misconfigured."""


def _get_key_registry() -> dict[str, bytes]:
    """Load all signing keys from ``TRUST_CENTER_SIGNING_KEYS`` (JSON array).

    Each entry must be ``{"kid": "...", "key_pem": "-----BEGIN ...", "active": bool}``.
    Falls back to ``TRUST_CENTER_SIGNING_KEY`` (single key) mapped as ``kid="v1"``.
    Returns a dict mapping *kid* → PEM bytes.
    """
    import json as _json

    raw_multi = os.environ.get("TRUST_CENTER_SIGNING_KEYS")
    if raw_multi:
        entries = _json.loads(raw_multi)
        return {e["kid"]: e["key_pem"].encode() for e in entries}

    # Fallback: legacy single-key env var → kid "v1"
    return {"v1": _get_signing_key_pem()}


def _get_active_signing_key() -> tuple[str, bytes]:
    """Return ``(kid, pem_bytes)`` for the currently *active* signing key.

    With multi-key config (``TRUST_CENTER_SIGNING_KEYS``), the entry with
    ``"active": true`` is returned.  With legacy single-key config, returns
    ``("v1", <pem>)``.

    Raises :class:`KeyRegistryError` when the registry is empty.
    """
    import json as _json

    raw_multi = os.environ.get("TRUST_CENTER_SIGNING_KEYS")
    if raw_multi:
        entries = _json.loads(raw_multi)
        if not entries:
            raise KeyRegistryError(
                "Key-Registry ist leer. TRUST_CENTER_SIGNING_KEYS konfigurieren."
            )
        for e in entries:
            if e.get("active"):
                return e["kid"], e["key_pem"].encode()
        # No active key found – fall back to last entry
        last = entries[-1]
        return last["kid"], last["key_pem"].encode()

    return "v1", _get_signing_key_pem()


def _compute_key_fingerprint(key_pem: bytes) -> str:
    """Compute SHA-256 fingerprint of the public key encoded in *key_pem*."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = serialization.load_pem_private_key(key_pem, password=None)
    assert isinstance(private_key, ec.EllipticCurvePrivateKey)
    pub_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(pub_der).hexdigest()


def _resolve_legacy_kid(
    cert_fingerprint: str | None, registry: dict[str, bytes]
) -> tuple[str, str]:
    """Resolve a legacy bundle (no ``signing_key_id``) to its registry ``kid``.

    Fallback chain:
    1. Fingerprint match against all keys in the registry.
    2. Singleton — if the registry has exactly one key, use it.
    3. Explicit ``kid="v1"`` entry in the registry.
    4. Raise ``KeyRegistryError``.

    Returns ``(kid, method)`` where *method* is one of
    ``"fingerprint"``, ``"singleton"``, ``"default_v1"``.
    """
    import hmac

    # 1. Fingerprint match (constant-time comparison)
    if cert_fingerprint:
        for kid, key_pem in registry.items():
            try:
                fp = _compute_key_fingerprint(key_pem)
                if hmac.compare_digest(fp, cert_fingerprint):
                    return kid, "fingerprint"
            except Exception:  # noqa: BLE001
                logging.getLogger(__name__).debug("fingerprint computation failed for kid=%s", kid)
                continue

    # 2. Singleton registry
    if len(registry) == 1:
        only_kid = next(iter(registry))
        return only_kid, "singleton"

    # 3. Default v1
    if "v1" in registry:
        return "v1", "default_v1"

    raise KeyRegistryError(
        "Legacy-Bundle kann keinem Schlüssel zugeordnet werden – "
        "kein Fingerprint-Match, kein Singleton, kein kid='v1'."
    )


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

    kid, key_pem = _get_active_signing_key()
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
    row.signing_key_id = kid
    row.signed_payload = payload.decode()
    # Store signed_payload + kid in metadata_json as well for backward
    # compatibility – verify reads from DB columns first, falling back to
    # metadata for Phase-11 bundles that lack the dedicated columns.
    meta = dict(row.metadata_payload or {})
    meta["signed_payload"] = payload.decode()
    meta["kid"] = kid
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

    Uses the key registry to look up the historical signing key by ``kid``.
    Validates payload binding (bundle_id + tenant_id) against the DB row.
    Returns an extended dict with ``valid``, ``signed_at``, ``signer_role``,
    ``key_id``, ``key_fingerprint``, ``payload_binding``, ``long_term_valid``
    or ``None`` when the bundle does not exist.
    """
    import logging

    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    logger = logging.getLogger(__name__)

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
            "key_id": None,
            "key_fingerprint": None,
            "payload_binding": "not_signed",
            "long_term_valid": False,
            "legacy_lookup_method": None,
            "reason": "Bundle ist nicht signiert.",
        }

    # Determine the kid used to sign this bundle.
    # Phase-12 bundles store kid in the DB column; Phase-11 bundles don't.
    kid = getattr(row, "signing_key_id", None)
    legacy_lookup_method: str | None = None

    registry = _get_key_registry()

    if not kid:
        meta = row.metadata_payload or {}
        kid_from_meta = meta.get("kid")
        if kid_from_meta and kid_from_meta in registry:
            kid = kid_from_meta
        else:
            # Phase-11 legacy bundle – resolve via fingerprint / singleton / v1
            try:
                kid, legacy_lookup_method = _resolve_legacy_kid(row.cert_fingerprint, registry)
            except KeyRegistryError:
                return {
                    "valid": False,
                    "signed_at": row.signed_at.isoformat() if row.signed_at else None,
                    "signer_role": row.signed_by_role,
                    "key_id": None,
                    "key_fingerprint": row.cert_fingerprint,
                    "payload_binding": "unknown_key",
                    "long_term_valid": False,
                    "legacy_lookup_method": None,
                    "reason": ("Legacy-Bundle kann keinem Schlüssel zugeordnet werden."),
                }

    # Look up the signing key from the registry
    if kid not in registry:
        return {
            "valid": False,
            "signed_at": row.signed_at.isoformat() if row.signed_at else None,
            "signer_role": row.signed_by_role,
            "key_id": kid,
            "key_fingerprint": row.cert_fingerprint,
            "payload_binding": "unknown_key",
            "long_term_valid": False,
            "legacy_lookup_method": legacy_lookup_method,
            "reason": (
                f"Schlüssel '{kid}' nicht mehr verfügbar – Langzeit-Verifikation nicht möglich."
            ),
        }

    # Retrieve the signed payload: prefer DB column (Phase 12), fall back
    # to metadata_json (Phase 11 backward compat).
    signed_payload_str = getattr(row, "signed_payload", None)
    if not signed_payload_str:
        meta = row.metadata_payload or {}
        signed_payload_str = meta.get("signed_payload")
    if not signed_payload_str:
        return {
            "valid": False,
            "signed_at": row.signed_at.isoformat() if row.signed_at else None,
            "signer_role": row.signed_by_role,
            "key_id": kid,
            "key_fingerprint": row.cert_fingerprint,
            "payload_binding": "missing_payload",
            "long_term_valid": False,
            "legacy_lookup_method": legacy_lookup_method,
            "reason": "Signierter Payload fehlt – Signatur nicht verifizierbar.",
        }

    # --- Payload-Binding Check (Anti-Transplant) ---
    try:
        parts = signed_payload_str.split("|")
        payload_bundle_id = parts[0] if len(parts) >= 1 else None
        payload_tenant_id = parts[1] if len(parts) >= 2 else None
    except Exception:
        payload_bundle_id = None
        payload_tenant_id = None

    if payload_bundle_id != row.id or payload_tenant_id != row.tenant_id:
        logger.critical(
            "PAYLOAD_BINDING_VIOLATION: bundle=%s tenant=%s – "
            "signed payload references bundle=%s tenant=%s. "
            "Possible signature transplant attack.",
            row.id,
            row.tenant_id,
            payload_bundle_id,
            payload_tenant_id,
        )
        return {
            "valid": False,
            "signed_at": row.signed_at.isoformat() if row.signed_at else None,
            "signer_role": row.signed_by_role,
            "key_id": kid,
            "key_fingerprint": row.cert_fingerprint,
            "payload_binding": "violation",
            "long_term_valid": False,
            "legacy_lookup_method": legacy_lookup_method,
            "reason": "Payload-Binding-Verletzung: Bundle-ID oder Tenant-ID stimmt nicht überein.",
        }

    # --- Cryptographic Verification ---
    try:
        key_pem = registry[kid]
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
            "key_id": kid,
            "key_fingerprint": row.cert_fingerprint,
            "payload_binding": "verified",
            "long_term_valid": True,
            "legacy_lookup_method": legacy_lookup_method,
        }
    except Exception:
        return {
            "valid": False,
            "signed_at": row.signed_at.isoformat() if row.signed_at else None,
            "signer_role": row.signed_by_role,
            "key_id": kid,
            "key_fingerprint": row.cert_fingerprint,
            "payload_binding": "verified",
            "long_term_valid": False,
            "legacy_lookup_method": legacy_lookup_method,
            "reason": "Signaturprüfung fehlgeschlagen – Integrität nicht bestätigt.",
        }


def get_key_registry_health() -> dict[str, Any]:
    """Return key-registry health status (no key material exposed)."""
    registry = _get_key_registry()
    active_kid: str | None = None
    key_count = len(registry)

    try:
        active_kid, _ = _get_active_signing_key()
    except KeyRegistryError:
        pass

    # Compute fingerprints only – never expose key material
    key_info = []
    for kid, key_pem in registry.items():
        try:
            fp = _compute_key_fingerprint(key_pem)
        except Exception:  # noqa: BLE001
            logging.getLogger(__name__).debug(
                "health: fingerprint computation failed for kid=%s", kid
            )
            fp = "error"
        key_info.append({"kid": kid, "fingerprint": fp})

    return {
        "registry_configured": key_count > 0,
        "active_key_id": active_kid,
        "key_count": key_count,
        "keys": key_info,
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
