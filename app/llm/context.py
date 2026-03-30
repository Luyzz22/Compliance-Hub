"""Structured context for LLM calls (logging, EU AI Act traceability)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LlmCallContext(BaseModel):
    """Tenant-scoped call metadata for guardrails and audit-style logs."""

    tenant_id: str = Field(min_length=1)
    user_role: str = Field(default="", max_length=64)
    action_name: str = Field(default="", max_length=128)
