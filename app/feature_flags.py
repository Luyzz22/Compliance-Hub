"""Feature-Flags (ENV-gesteuert, optional später tenant-spezifisch erweiterbar)."""

from __future__ import annotations

import os
from enum import StrEnum
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class FeatureFlag(StrEnum):
    advisor_workspace = "advisor_workspace"
    api_keys_ui = "api_keys_ui"
    demo_seeding = "demo_seeding"
    evidence_uploads = "evidence_uploads"
    guided_setup = "guided_setup"
    pilot_runbook = "pilot_runbook"


_FLAG_ENV_KEYS: dict[FeatureFlag, str] = {
    FeatureFlag.advisor_workspace: "COMPLIANCEHUB_FEATURE_ADVISOR_WORKSPACE",
    FeatureFlag.api_keys_ui: "COMPLIANCEHUB_FEATURE_API_KEYS_UI",
    FeatureFlag.demo_seeding: "COMPLIANCEHUB_FEATURE_DEMO_SEEDING",
    FeatureFlag.evidence_uploads: "COMPLIANCEHUB_FEATURE_EVIDENCE_UPLOADS",
    FeatureFlag.guided_setup: "COMPLIANCEHUB_FEATURE_GUIDED_SETUP",
    FeatureFlag.pilot_runbook: "COMPLIANCEHUB_FEATURE_PILOT_RUNBOOK",
}


def _parse_env_bool(key: str, *, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def is_feature_enabled(
    flag: FeatureFlag,
    tenant_id: str | None = None,
    *,
    session: Session | None = None,
) -> bool:
    """
    Prüft, ob ein Feature aktiv ist.

    Mit tenant_id und session: zuerst Override in tenant_feature_flag_overrides, sonst ENV.
    """
    if tenant_id is not None and session is not None:
        from app.repositories.tenant_feature_overrides import TenantFeatureOverrideRepository

        repo = TenantFeatureOverrideRepository(session)
        override = repo.get_override(tenant_id, flag.value)
        if override is not None:
            return override

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
