"""Fail-closed request and daily usage limits for governed LLM calls."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.services import llm_client

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class LLMUsagePolicyExceeded(PermissionError):
    """The configured request or daily LLM budget has been exhausted."""


@dataclass(frozen=True)
class LLMUsagePolicy:
    max_prompt_characters: int
    daily_call_limit: int
    daily_token_limit: int


def _bounded_integer(name: str, *, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise llm_client.LLMConfigurationError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise llm_client.LLMConfigurationError(
            f"{name} must be between {minimum} and {maximum}",
        )
    return value


def current_llm_usage_policy() -> LLMUsagePolicy:
    """Resolve bounded runtime limits; zero disables only the daily counters."""
    return LLMUsagePolicy(
        max_prompt_characters=_bounded_integer(
            "COMPLIANCEHUB_LLM_MAX_PROMPT_CHARACTERS",
            default=48_000,
            minimum=256,
            maximum=48_000,
        ),
        daily_call_limit=_bounded_integer(
            "COMPLIANCEHUB_LLM_DAILY_CALL_LIMIT",
            default=0,
            minimum=0,
            maximum=100_000,
        ),
        daily_token_limit=_bounded_integer(
            "COMPLIANCEHUB_LLM_DAILY_TOKEN_LIMIT",
            default=0,
            minimum=0,
            maximum=100_000_000,
        ),
    )


def enforce_llm_usage_policy(
    session: Session | None,
    *,
    tenant_id: str,
    prompt: str,
    projected_output_tokens: int,
) -> None:
    """Reject a call before egress when request or daily limits would be exceeded."""
    policy = current_llm_usage_policy()
    if len(prompt) > policy.max_prompt_characters:
        raise LLMUsagePolicyExceeded("LLM prompt exceeds the configured character limit")

    if policy.daily_call_limit == 0 and policy.daily_token_limit == 0:
        return
    if session is None:
        raise llm_client.LLMConfigurationError(
            "Configured daily LLM limits require a database-backed router session",
        )

    from app.repositories.llm_call_metadata import LLMCallMetadataRepository

    projected_input_tokens = max(1, len(prompt) // 4)
    projected_total = projected_input_tokens + projected_output_tokens
    usage_day_utc = datetime.now(UTC).date().isoformat()
    accepted = LLMCallMetadataRepository(session).reserve_daily_usage(
        tenant_id,
        usage_day_utc=usage_day_utc,
        projected_tokens=projected_total,
        call_limit=policy.daily_call_limit,
        token_limit=policy.daily_token_limit,
    )
    if not accepted:
        raise LLMUsagePolicyExceeded("Daily LLM call budget or token budget is exhausted")
