"""Feature-Flags (ENV-gesteuert, optional später tenant-spezifisch erweiterbar)."""

from __future__ import annotations

import os
from enum import StrEnum

from fastapi import HTTPException, status


class FeatureFlag(StrEnum):
    advisor_workspace = "advisor_workspace"
    demo_seeding = "demo_seeding"
    evidence_uploads = "evidence_uploads"
    guided_setup = "guided_setup"


_FLAG_ENV_KEYS: dict[FeatureFlag, str] = {
    FeatureFlag.advisor_workspace: "COMPLIANCEHUB_FEATURE_ADVISOR_WORKSPACE",
    FeatureFlag.demo_seeding: "COMPLIANCEHUB_FEATURE_DEMO_SEEDING",
    FeatureFlag.evidence_uploads: "COMPLIANCEHUB_FEATURE_EVIDENCE_UPLOADS",
    FeatureFlag.guided_setup: "COMPLIANCEHUB_FEATURE_GUIDED_SETUP",
}


def _parse_env_bool(key: str, *, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def is_feature_enabled(flag: FeatureFlag, tenant_id: str | None = None) -> bool:
    """
    Prüft, ob ein Feature aktiv ist.

    tenant_id: reserviert für künftige Mandanten-Overrides (derzeit ungenutzt).
    """
    _ = tenant_id
    env_key = _FLAG_ENV_KEYS[flag]
    # Standard: an, damit bestehende Umgebungen und Tests ohne neue ENV-Variablen funktionieren.
    return _parse_env_bool(env_key, default=True)


def create_feature_guard(flag: FeatureFlag):
    """FastAPI-Depends: 403, wenn Feature ausgeschaltet."""

    def _guard() -> None:
        if not is_feature_enabled(flag):
            env_key = _FLAG_ENV_KEYS[flag]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Feature '{flag.value}' is disabled. Enable via {env_key}=true "
                    f"(omit or set true for default-on in dev)."
                ),
            )

    return _guard
