"""API- und Ergebnis-Modelle für Demo-Tenant-Seeding (nur Demo-/Pilot-Umgebungen)."""

from __future__ import annotations

from typing import Literal

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
    demo_governance_telemetry_events_inserted: int = Field(
        default=0,
        description="usage_events für GAI (Governance Activity Index), idempotent.",
    )
    demo_governance_runtime_events_inserted: int = Field(
        default=0,
        description="Neue ai_runtime_events (synthetisch) für OAMI-Demo.",
    )
    demo_oami_snapshot_refreshed: bool = Field(
        default=False,
        description="Tenant-OAMI-Snapshot nach Seed neu persistiert.",
    )


class DemoGovernanceMaturityLayerRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=255)


class DemoGovernanceMaturityLayerResponse(BaseModel):
    tenant_id: str
    telemetry_events_inserted: int
    runtime_events_inserted: int
    oami_snapshot_persisted: bool
    skipped_already_seeded: bool


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
    workspace_mode: Literal["production", "demo", "playground"] = Field(
        ...,
        description="production | demo (read-only) | playground (sandbox writes allowed).",
    )
    mode_label: str = Field(
        ...,
        max_length=255,
        description="Kurzlabel für Shell/Banner (Deutsch).",
    )
    mode_hint: str = Field(
        ...,
        max_length=512,
        description="Einzeiler für Tooltip/Banner (Deutsch).",
    )
    demo_mode_feature_enabled: bool = Field(
        default=False,
        description="COMPLIANCEHUB_FEATURE_DEMO_MODE – spiegelt Server-ENV für UI-Kohärenz.",
    )
    feature_ai_act_evidence_views: bool = Field(
        default=False,
        description="COMPLIANCEHUB_FEATURE_AI_ACT_EVIDENCE_VIEWS für diesen Mandanten aktiv.",
    )
    can_view_ai_evidence: bool = Field(
        default=False,
        description=(
            "OPA-Erlaubnis für Aktion view_ai_evidence; nutzt x-opa-user-role / "
            "COMPLIANCEHUB_OPA_ROLE_AI_EVIDENCE wie die Evidence-API."
        ),
    )
