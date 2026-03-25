"""Pydantic: AI-KPI/KRI API (Systemwerte, Mandanten-Summary)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AiKpiDefinitionRead(BaseModel):
    id: str
    key: str
    name: str
    description: str
    category: str
    unit: str
    recommended_direction: Literal["up", "down"]
    framework_tags: list[str] = Field(default_factory=list)


class AiSystemKpiValueRead(BaseModel):
    id: str
    period_start: datetime
    period_end: datetime
    value: float
    source: str
    comment: str | None = None


class AiSystemKpiSeriesRead(BaseModel):
    definition: AiKpiDefinitionRead
    periods: list[AiSystemKpiValueRead]
    trend: Literal["up", "down", "flat"]
    latest_status: Literal["ok", "red"]


class AiSystemKpisListResponse(BaseModel):
    ai_system_id: str
    series: list[AiSystemKpiSeriesRead]


class AiSystemKpiUpsertBody(BaseModel):
    """Anlegen/Aktualisieren eines Periodenwerts (Upsert über period_start)."""

    kpi_definition_id: str = Field(..., min_length=1, max_length=36)
    period_start: datetime
    period_end: datetime
    value: float
    source: Literal["manual", "api", "import"] = "manual"
    comment: str | None = Field(default=None, max_length=4000)


class AiSystemKpiUpsertResponse(BaseModel):
    id: str
    kpi_definition_id: str
    period_start: datetime
    period_end: datetime
    value: float
    source: str
    comment: str | None = None


class AiKpiPerKpiAggregateRead(BaseModel):
    kpi_key: str
    name: str
    unit: str
    category: str
    avg_latest: float | None = None
    min_latest: float | None = None
    max_latest: float | None = None
    trend: Literal["up", "down", "flat"]
    systems_with_data: int = Field(ge=0)


class AiSystemCriticalKpiRead(BaseModel):
    kpi_key: str
    name: str
    value: float
    unit: str


class AiSystemCriticalRowRead(BaseModel):
    ai_system_id: str
    ai_system_name: str
    risk_level: str
    critical_kpis: list[AiSystemCriticalKpiRead]


class AiKpiSummaryResponse(BaseModel):
    per_kpi: list[AiKpiPerKpiAggregateRead]
    per_system_critical: list[AiSystemCriticalRowRead]
    high_risk_system_count: int = Field(ge=0)
