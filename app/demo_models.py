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
