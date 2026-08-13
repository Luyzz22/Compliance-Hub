from __future__ import annotations

import os
import secrets
from functools import lru_cache
from typing import Annotated

from cryptography.hazmat.primitives import hashes, hmac
from fastapi import Header, HTTPException, status
from pydantic import BaseModel, Field

from app.secret_files import production_runtime, read_secret


class AuthContext(BaseModel):
    tenant_id: str
    api_key: str = Field(default="", exclude=True, repr=False)
    user_id: str | None = None
    role: str | None = None
    session_id: str | None = None
    auth_method: str | None = None
    credential_kind: str = "api_key"

    @property
    def actor_id(self) -> str:
        """Stable audit subject that never persists the bearer credential."""
        if self.user_id:
            return f"user:{self.user_id}"
        digest = hash_api_key(self.api_key)
        return f"api_key:hmac-sha256:{digest[:16]}"


class SecuritySettings(BaseModel):
    api_keys: list[str] = Field(default_factory=list)

    @classmethod
    def from_env(cls) -> SecuritySettings:
        raw_keys = os.getenv("COMPLIANCEHUB_API_KEYS", "")
        keys = [key.strip() for key in raw_keys.split(",") if key.strip()]
        return cls(api_keys=keys)


@lru_cache
def get_settings() -> SecuritySettings:
    return SecuritySettings.from_env()


def secret_matches_any(candidate: str, allowed: list[str] | frozenset[str]) -> bool:
    """Compare bearer credentials without data-dependent early equality checks."""
    value = str(candidate).strip()
    return bool(value) and any(secrets.compare_digest(value, expected) for expected in allowed)


def validate_api_key_only(x_api_key: str | None) -> str:
    """Prüft nur den API-Key (ohne Tenant-Header), z. B. für Advisor-Portfolio."""
    if x_api_key is None or not x_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    settings = get_settings()
    if not secret_matches_any(x_api_key, settings.api_keys):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return x_api_key.strip()


def advisor_id_allowlist() -> frozenset[str] | None:
    """
    COMPLIANCEHUB_ADVISOR_IDS=advisor-a@x.com,advisor-b@x.com

    Wenn gesetzt, dürfen nur diese advisor_ids Advisor-Endpunkte nutzen.
    ``None`` bedeutet "nicht konfiguriert" – in Produktion wird das von
    :func:`require_advisor_allowlist_configured` als Fehlkonfiguration behandelt.
    """
    raw = os.getenv("COMPLIANCEHUB_ADVISOR_IDS", "").strip()
    if not raw:
        return None
    ids = {part.strip() for part in raw.split(",") if part.strip()}
    return frozenset(ids) if ids else None


def require_advisor_allowlist_configured() -> frozenset[str] | None:
    """
    Erzwingt eine konfigurierte Advisor-Allowlist in Produktion.

    Die Advisor-Endpunkte identifizieren den Berater über den selbstdeklarierten
    ``x-advisor-id``-Header. Ohne Allowlist könnte jeder Inhaber eines gültigen
    API-Keys eine beliebige ``advisor_id`` behaupten. In Produktion ist die Allowlist
    deshalb Pflicht; fehlt sie, wird der Zugriff verweigert statt stillschweigend
    geöffnet.
    """
    allowed = advisor_id_allowlist()
    if allowed is not None:
        return allowed
    environment = os.getenv("COMPLIANCEHUB_ENV", "dev").strip().lower()
    if environment in {"prod", "production"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Advisor access is disabled (COMPLIANCEHUB_ADVISOR_IDS not configured)",
        )
    return None


def require_advisor_api_access(
    advisor_id: str,
    x_advisor_id: Annotated[str | None, Header(alias="x-advisor-id")] = None,
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
) -> str:
    """
    Berater-Portfolio: gültiger API-Key, Pfad-advisor_id muss mit x-advisor-id übereinstimmen.
    """
    validate_api_key_only(x_api_key)
    if x_advisor_id is None or not str(x_advisor_id).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing x-advisor-id header",
        )
    if str(x_advisor_id).strip() != advisor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advisor ID mismatch with x-advisor-id header",
        )
    allowed = require_advisor_allowlist_configured()
    if allowed is not None and advisor_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advisor not authorized for portfolio access",
        )
    return advisor_id


def require_advisor_rag_headers(
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
    x_advisor_id: Annotated[str | None, Header(alias="x-advisor-id")] = None,
) -> str:
    """
    Advisor Knowledge-Hub RAG: gültiger API-Key und ``x-advisor-id`` (ohne Pfad-Parameter).
    """
    validate_api_key_only(x_api_key)
    if x_advisor_id is None or not str(x_advisor_id).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing x-advisor-id header",
        )
    aid = str(x_advisor_id).strip()
    allowed = require_advisor_allowlist_configured()
    if allowed is not None and aid not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advisor not authorized for RAG access",
        )
    return aid


def hash_api_key(raw: str) -> str:
    """Deterministic, peppered lookup digest for opaque API keys and sessions."""

    pepper = read_secret(
        "COMPLIANCEHUB_CREDENTIAL_PEPPER",
        "COMPLIANCEHUB_CREDENTIAL_PEPPER_FILE",
        required=production_runtime(),
        minimum_characters=32,
    )
    if not pepper:
        pepper = "compliancehub-development-credential-pepper-only"
    lookup_mac = hmac.HMAC(pepper.encode("utf-8"), hashes.SHA256())
    lookup_mac.update(raw.encode("utf-8"))
    return lookup_mac.finalize().hex()


def admin_provision_api_keys() -> frozenset[str]:
    """COMPLIANCEHUB_ADMIN_API_KEYS – komma-separiert, für POST /tenants/provision."""
    raw = os.getenv("COMPLIANCEHUB_ADMIN_API_KEYS", "").strip()
    if not raw:
        return frozenset()
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def require_admin_provision_api_key(
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
) -> str:
    allowed = admin_provision_api_keys()
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tenant provisioning is disabled (no COMPLIANCEHUB_ADMIN_API_KEYS)",
        )
    if x_api_key is None or not str(x_api_key).strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    key = str(x_api_key).strip()
    if not secret_matches_any(key, allowed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key",
        )
    return key


def demo_seed_api_keys() -> frozenset[str]:
    """API-Keys, die POST /api/v1/demo/tenants/seed und Template-Liste nutzen dürfen."""
    raw = os.getenv("COMPLIANCEHUB_DEMO_SEED_API_KEYS", "").strip()
    if not raw:
        return frozenset()
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def demo_seed_tenant_allowlist() -> frozenset[str] | None:
    """Wenn gesetzt, dürfen nur diese tenant_ids geseedet werden (Komma-getrennt)."""
    raw = os.getenv("COMPLIANCEHUB_DEMO_SEED_TENANT_IDS", "").strip()
    if not raw:
        return None
    ids = {part.strip() for part in raw.split(",") if part.strip()}
    return frozenset(ids) if ids else None


def require_demo_seed_api_key(
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
) -> str:
    """
    Schützt Demo-Seeding: eigener Key-Pool, unabhängig vom normalen Mandanten-API-Key.
    """
    keys = demo_seed_api_keys()
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demo seeding is disabled (no COMPLIANCEHUB_DEMO_SEED_API_KEYS)",
        )
    if x_api_key is None or not str(x_api_key).strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    key = str(x_api_key).strip()
    if not secret_matches_any(key, keys):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid demo seed API key",
        )
    return key


def ensure_demo_tenant_seed_allowed(tenant_id: str) -> None:
    allowed = demo_seed_tenant_allowlist()
    if allowed is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo tenant allowlist not configured (set COMPLIANCEHUB_DEMO_SEED_TENANT_IDS)",
        )
    if tenant_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is not in COMPLIANCEHUB_DEMO_SEED_TENANT_IDS",
        )


def delete_evidence_allowed_for_api_key(api_key: str) -> bool:
    """Nur API-Keys in COMPLIANCEHUB_EVIDENCE_DELETE_API_KEYS dürfen Evidence löschen."""
    raw = os.getenv("COMPLIANCEHUB_EVIDENCE_DELETE_API_KEYS", "")
    allowed = [k.strip() for k in raw.split(",") if k.strip()]
    if not allowed:
        return False
    return secret_matches_any(api_key, allowed)
