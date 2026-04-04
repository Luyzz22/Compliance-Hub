"""Board Readiness (Wave 34) – governance-side DTOs for executive / internal dashboards.

Aggregations are primarily computed in the Next.js admin layer via tenant-scoped APIs;
these models document the contract and support future FastAPI endpoints or imports.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class BoardReadinessTraffic(StrEnum):
    """Coarse RAG-style signal (no numeric vanity score at pillar level)."""

    green = "green"
    amber = "amber"
    red = "red"


class BoardReadinessPillarKey(StrEnum):
    eu_ai_act = "eu_ai_act"
    iso_42001 = "iso_42001"
    nis2 = "nis2"
    dsgvo = "dsgvo"


class BoardReadinessSubIndicator(BaseModel):
    """Single auditable metric within a pillar."""

    key: str = Field(description="Stable machine key, e.g. high_risk_art9_complete_ratio")
    label_de: str
    value_percent: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="0–100 where applicable; None if not computable.",
    )
    value_count: int | None = Field(default=None, ge=0, description="Numerator or absolute count.")
    value_denominator: int | None = Field(default=None, ge=0)
    status: BoardReadinessTraffic
    source_api_paths: list[str] = Field(
        default_factory=list,
        description="Underlying REST paths used to derive the indicator.",
    )


class BoardReadinessPillarBlock(BaseModel):
    pillar: BoardReadinessPillarKey
    title_de: str
    summary_de: str
    status: BoardReadinessTraffic
    indicators: list[BoardReadinessSubIndicator] = Field(default_factory=list)


class BoardAttentionItem(BaseModel):
    """Row for the Board Attention list (governance debt)."""

    id: str
    severity: BoardReadinessTraffic
    tenant_id: str
    tenant_label: str | None = None
    segment_tag: str | None = Field(default=None, description="GTM segment bucket or ICP label.")
    readiness_class: str | None = Field(default=None, description="Wave 33 readiness class.")
    subject_type: str = Field(description="ai_system | tenant")
    subject_id: str | None = None
    subject_name: str | None = None
    missing_artefact_de: str
    last_change_at: str | None = Field(
        default=None,
        description="ISO-8601 from underlying entity when available.",
    )
    deep_links: dict[str, str] = Field(
        default_factory=dict,
        description="workspace_path / api_path keys for drill-down.",
    )
