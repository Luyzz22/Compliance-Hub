"""Shared internal deep-health computation (HTTP route + operational poller)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast

from sqlalchemy import text
from sqlalchemy.orm import Session

from app import sovereignty
from app.llm_models import LLMProvider
from app.policy.opa_client import evaluate_action_policy
from app.services.llm_client import is_provider_configured
from app.services.llm_router import llama_endpoint_is_private

logger = logging.getLogger(__name__)

InternalHealthSignal = Literal["up", "degraded", "down"]


@dataclass(frozen=True)
class InternalDeepHealthDTO:
    app: InternalHealthSignal
    db: InternalHealthSignal
    policy_engine: InternalHealthSignal
    external_ai_provider: InternalHealthSignal
    timestamp: datetime


def _external_ai_provider_signal() -> InternalHealthSignal:
    override = os.getenv("INTERNAL_HEALTH_AI_PROVIDER_SIGNAL", "").strip().lower()
    if override == "up" or override == "degraded" or override == "down":
        return cast(InternalHealthSignal, override)
    feature_enabled = os.getenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not feature_enabled:
        return "up"
    allowed_providers = sovereignty.allowed_llm_providers()

    def approved_runtime_posture(provider: LLMProvider) -> bool:
        if provider.value not in allowed_providers or not is_provider_configured(provider):
            return False
        if provider is LLMProvider.LLAMA:
            return llama_endpoint_is_private()
        if (
            provider is LLMProvider.AZURE_OPENAI
            and sovereignty.current_mode() is not sovereignty.SovereigntyMode.UNRESTRICTED
        ):
            return os.getenv("COMPLIANCEHUB_LLM_ASSUME_AZURE_EU", "").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        return True

    has_configured_allowed_provider = any(
        approved_runtime_posture(provider) for provider in LLMProvider
    )
    return "up" if has_configured_allowed_provider else "down"


def compute_internal_deep_health(session: Session) -> InternalDeepHealthDTO:
    """DB, policy engine and AI posture; same semantics as GET /api/internal/health."""
    db_status: InternalHealthSignal = "down"
    try:
        session.execute(text("SELECT 1"))
        db_status = "up"
    except Exception:
        logger.exception("internal health DB check failed")
        db_status = "down"

    policy_decision = evaluate_action_policy(
        {
            "action": "readiness_probe",
            "user_role": "readiness_probe",
            "risk_score": 1.0,
        }
    )
    production = os.getenv("COMPLIANCEHUB_ENV", "dev").strip().lower() in {
        "prod",
        "production",
    }
    policy_status: InternalHealthSignal = (
        "up"
        if policy_decision.reason == "opa_deny"
        or (policy_decision.reason == "opa_disabled" and not production)
        else "down"
    )

    return InternalDeepHealthDTO(
        app="up",
        db=db_status,
        policy_engine=policy_status,
        external_ai_provider=_external_ai_provider_signal(),
        timestamp=datetime.now(UTC),
    )
