"""LLM layer exceptions (contracts, guardrails)."""

from __future__ import annotations


class LLMContractViolation(Exception):
    """Raised when LLM output does not validate against the expected Pydantic contract."""
