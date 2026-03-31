"""Integration domain model — outbox jobs for DATEV/SAP/BTP connectors.

Stable contracts for enterprise outbound synchronisation.  Jobs are
created via the outbox pattern and dispatched by connector stubs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _job_id() -> str:
    return f"INTJOB-{uuid.uuid4().hex[:12]}"


class IntegrationTarget(StrEnum):
    datev_export = "datev_export"
    sap_btp = "sap_btp"
    generic_partner_api = "generic_partner_api"


class IntegrationJobStatus(StrEnum):
    pending = "pending"
    dispatched = "dispatched"
    delivered = "delivered"
    failed = "failed"
    dead_letter = "dead_letter"


class IntegrationPayloadType(StrEnum):
    ai_risk_assessment = "ai_risk_assessment"
    nis2_obligation = "nis2_obligation"
    iso42001_gap = "iso42001_gap"
    board_report_summary = "board_report_summary"
    ai_system_readiness_snapshot = "ai_system_readiness_snapshot"


MAX_DISPATCH_ATTEMPTS = 3


class IntegrationJob(BaseModel):
    job_id: str = Field(default_factory=_job_id)
    tenant_id: str = ""
    client_id: str = ""
    system_id: str = ""

    target: IntegrationTarget = IntegrationTarget.generic_partner_api
    payload_type: IntegrationPayloadType = IntegrationPayloadType.ai_risk_assessment
    payload_version: str = "v1"
    payload: dict[str, Any] = Field(default_factory=dict)

    status: IntegrationJobStatus = IntegrationJobStatus.pending
    idempotency_key: str = ""

    source_entity_type: str = ""
    source_entity_id: str = ""
    trace_id: str = ""

    created_at: str = Field(default_factory=_now_iso)
    last_attempt_at: str = ""
    attempt_count: int = 0

    last_dispatch_result: str = ""


class DispatchResult(BaseModel):
    success: bool = False
    message: str = ""
    connector_ref: str = ""
