"""Shared internal deep-health computation (HTTP route + operational poller)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

InternalHealthSignal = Literal["up", "degraded", "down"]


@dataclass(frozen=True)
class InternalDeepHealthDTO:
    app: InternalHealthSignal
    db: InternalHealthSignal
    external_ai_provider: InternalHealthSignal
    timestamp: datetime


def _external_ai_provider_signal() -> InternalHealthSignal:
    override = os.getenv("INTERNAL_HEALTH_AI_PROVIDER_SIGNAL", "").strip().lower()
    if override == "up" or override == "degraded" or override == "down":
        return cast(InternalHealthSignal, override)
    has_any_key = any(
        os.getenv(name, "").strip()
        for name in (
            "ANTHROPIC_API_KEY",
            "CLAUDE_API_KEY",
            "OPENAI_API_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
        )
    )
    return "up" if has_any_key else "degraded"


def compute_internal_deep_health(session: Session) -> InternalDeepHealthDTO:
    """DB connectivity + AI credential posture; same semantics as GET /api/internal/health."""
    db_status: InternalHealthSignal = "down"
    try:
        session.execute(text("SELECT 1"))
        db_status = "up"
    except Exception:
        logger.exception("internal health DB check failed")
        db_status = "down"

    return InternalDeepHealthDTO(
        app="up",
        db=db_status,
        external_ai_provider=_external_ai_provider_signal(),
        timestamp=datetime.now(UTC),
    )
