"""Pydantic schemas for deterministic governance board reporting (snapshot-based MVP)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TrendDirection = Literal["up", "down", "stable"]
TrafficLight = Literal["green", "amber", "red"]


class BoardReportGenerateRequest(BaseModel):
    period_key: str = Field(..., examples=["2026-04", "2026-Q2"])
    period_type: Literal["monthly", "quarterly"] = "monthly"
    period_start: datetime
    period_end: datetime
    title: str | None = Field(default=None, max_length=500)


class BoardMetricRead(BaseModel):
    metric_key: str
    label: str
    value: float
    unit: str = "count"
    traffic_light: TrafficLight
    trend_direction: TrendDirection
    trend_delta: float = 0.0
    narrative_de: str | None = None


class BoardReportListItemRead(BaseModel):
    id: str
    tenant_id: str
    period_key: str
    period_type: str
    title: str
    status: str
    generated_at_utc: datetime
    generated_by: str | None = None


class BoardActionRead(BaseModel):
    id: str
    action_title: str
    action_detail: str | None
    owner: str | None
    due_at: datetime | None
    status: str
    priority: str
    source_type: str
    source_id: str | None


class BoardReportSummaryRead(BaseModel):
    report_id: str
    period_key: str
    period_type: str
    generated_at_utc: datetime
    headline_de: str
    top_risk_areas: list[str]
    metrics: list[BoardMetricRead]
    resilience_summary_de: str


class BoardReportDetailRead(BaseModel):
    id: str
    tenant_id: str
    period_key: str
    period_type: str
    period_start: datetime
    period_end: datetime
    title: str
    status: str
    generated_at_utc: datetime
    generated_by: str | None
    summary: BoardReportSummaryRead
    actions: list[BoardActionRead]
    audit_trail: list[dict[str, str]]
