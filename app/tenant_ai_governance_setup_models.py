"""API-Modelle: AI-Governance-Setup-Wizard (Tenant)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TenantAIGovernanceSetupPatch(BaseModel):
    """Teil-Update; nur gesetzte Felder werden übernommen."""

    tenant_kind: Literal["enterprise", "advisor"] | None = None
    compliance_scopes: list[str] | None = None
    governance_roles: dict[str, str] | None = None
    active_frameworks: list[str] | None = None
    mark_steps_complete: list[int] | None = Field(
        default=None,
        description=(
            "Abgeschlossene oder übersprungene Wizard-Schritte (1–6); "
            "werden zur bestehenden Liste addiert."
        ),
    )
    flags: dict[str, bool] | None = None


class TenantAIGovernanceSetupResponse(BaseModel):
    tenant_id: str
    tenant_kind: str | None = None
    compliance_scopes: list[str] = Field(default_factory=list)
    governance_roles: dict[str, str] = Field(default_factory=dict)
    active_frameworks: list[str] = Field(default_factory=list)
    steps_marked_complete: list[int] = Field(default_factory=list)
    flags: dict[str, bool] = Field(default_factory=dict)
    progress_steps: list[int] = Field(
        default_factory=list,
        description="Vereinigung aus markierten und aus Mandantendaten abgeleiteten Schritten.",
    )
