"""Prompt builder must inject contract version, enums, and DE labels from single source."""

from __future__ import annotations

from app.governance_maturity_contract import (
    GOVERNANCE_MATURITY_CONTRACT_VERSION,
    INDEX_API_LEVELS,
    INDEX_LEVEL_DE,
    READINESS_API_LEVELS,
    READINESS_LEVEL_DE,
    regulatory_context_standard,
)
from app.services.readiness_explain_prompt import build_readiness_explain_prompt


def test_build_readiness_explain_prompt_includes_version_and_regulatory_block() -> None:
    p = build_readiness_explain_prompt(facts_envelope={"readiness": {"tenant_id": "t"}})
    assert GOVERNANCE_MATURITY_CONTRACT_VERSION in p
    assert "Explain-Contract-Version" in p
    assert regulatory_context_standard() in p


def test_prompt_contains_all_api_levels_and_german_labels_from_contract() -> None:
    p = build_readiness_explain_prompt(facts_envelope={})
    for api in READINESS_API_LEVELS:
        assert api in p
    for api in INDEX_API_LEVELS:
        assert api in p
    for label in READINESS_LEVEL_DE.values():
        assert label in p
    for label in INDEX_LEVEL_DE.values():
        assert label in p


def test_prompt_serializes_facts_envelope() -> None:
    p = build_readiness_explain_prompt(
        facts_envelope={"readiness": {"score": 42}, "governance_activity": None},
    )
    assert "readiness" in p and "42" in p
