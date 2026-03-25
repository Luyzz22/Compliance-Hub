"""API- und Ergebnis-Modelle für Demo-Tenant-Seeding (nur Demo-/Pilot-Umgebungen)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DemoSeedRequest(BaseModel):
    template_key: str = Field(..., min_length=1, max_length=64)
    tenant_id: str = Field(..., min_length=1, max_length=255)
    advisor_id: str | None = Field(
        default=None,
        max_length=320,
        description="Optional: Eintrag in advisor_tenants nach erfolgreichem Seed.",
    )


class DemoSeedResponse(BaseModel):
    template_key: str
    tenant_id: str
    ai_systems_count: int
    governance_actions_count: int
    evidence_files_count: int
    nis2_kpi_rows_count: int
    policy_rows_count: int
    classifications_count: int
    advisor_linked: bool
    board_reports_count: int = 0
    ai_kpi_value_rows_count: int = 0
    cross_reg_control_rows_count: int = 0


class TenantWorkspaceMetaResponse(BaseModel):
    """Öffentliche Mandanten-Stammdaten für Workspace-UI (keine Secrets)."""

    tenant_id: str
    display_name: str
    is_demo: bool
    demo_playground: bool
    mutation_blocked: bool = Field(
        default=False,
        description="True, wenn die API mutierende Requests (403 demo_tenant_readonly) ablehnt.",
    )
    demo_mode_feature_enabled: bool = Field(
        default=False,
        description="COMPLIANCEHUB_FEATURE_DEMO_MODE – spiegelt Server-ENV für UI-Kohärenz.",
    )
