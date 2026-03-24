from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class GovernanceActionStatus(StrEnum):
    open = "open"
    in_progress = "in_progress"
    done = "done"


class AIGovernanceActionCreate(BaseModel):
    related_ai_system_id: str | None = None
    related_requirement: str = Field(..., min_length=1, max_length=500)
    title: str = Field(..., min_length=1, max_length=500)
    status: GovernanceActionStatus = GovernanceActionStatus.open
    due_date: datetime | None = None
    owner: str | None = Field(default=None, max_length=320)


class AIGovernanceActionUpdate(BaseModel):
    related_ai_system_id: str | None = None
    related_requirement: str | None = Field(default=None, max_length=500)
    title: str | None = Field(default=None, max_length=500)
    status: GovernanceActionStatus | None = None
    due_date: datetime | None = None
    owner: str | None = Field(default=None, max_length=320)


class AIGovernanceActionRead(BaseModel):
    id: str
    tenant_id: str
    related_ai_system_id: str | None
    related_requirement: str
    title: str
    status: GovernanceActionStatus
    due_date: datetime | None
    owner: str | None
    created_at_utc: datetime
    updated_at_utc: datetime
