"""Structured advisor response models for GA and channel integrations.

Extends the existing AdvisorState with structured fields that SAP/DATEV
adapters can consume without parsing free-text answers.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.advisor.channels import AdvisorChannel, ChannelMetadata
from app.advisor.errors import AdvisorError


class AdvisorResponseMeta(BaseModel):
    """Metadata block included with every advisor response."""

    channel: AdvisorChannel = AdvisorChannel.web
    channel_metadata: ChannelMetadata | None = None
    request_id: str | None = None
    trace_id: str | None = None
    latency_ms: float | None = None
    is_cached: bool = False
    flow_type: str | None = None


class AdvisorStructuredResponse(BaseModel):
    """GA-ready structured advisor response.

    The `answer` field preserves backwards compatibility with web clients.
    Structured fields are additive for channel integrations.
    """

    answer: str = ""
    is_escalated: bool = False
    escalation_reason: str = ""
    confidence_level: str = "low"
    intent: str = ""

    tags: list[str] = Field(default_factory=list)
    suggested_next_steps: list[str] = Field(default_factory=list)
    ref_ids: dict[str, str] = Field(default_factory=dict)

    meta: AdvisorResponseMeta = Field(default_factory=AdvisorResponseMeta)
    error: AdvisorError | None = None
    needs_manual_followup: bool = False

    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
