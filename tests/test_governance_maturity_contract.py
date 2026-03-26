"""Guardrails: governance maturity API contract and LLM terminology strings."""

from __future__ import annotations

from app.governance_maturity_contract import (
    INDEX_API_LEVELS,
    INDEX_LEVEL_DE,
    READINESS_API_LEVELS,
    READINESS_LEVEL_DE,
    normalize_index_level,
    normalize_readiness_level,
    readiness_explain_json_schema_instructions,
    terminology_contract_for_llm_prompt,
)


def test_readiness_api_levels_match_frontend_cardinality() -> None:
    assert READINESS_API_LEVELS == ("basic", "managed", "embedded")


def test_index_api_levels_match_frontend_cardinality() -> None:
    assert INDEX_API_LEVELS == ("low", "medium", "high")


def test_german_labels_complete_for_all_api_levels() -> None:
    for k in READINESS_API_LEVELS:
        assert k in READINESS_LEVEL_DE and READINESS_LEVEL_DE[k]
    for k in INDEX_API_LEVELS:
        assert k in INDEX_LEVEL_DE and INDEX_LEVEL_DE[k]


def test_normalizers_accept_case_insensitive() -> None:
    assert normalize_readiness_level("MANAGED") == "managed"
    assert normalize_index_level("HIGH") == "high"
    assert normalize_readiness_level("nope") is None
    assert normalize_index_level("") is None


def test_llm_prompt_contains_fixed_german_stage_names() -> None:
    block = terminology_contract_for_llm_prompt()
    for word in ("Basis", "Etabliert", "Integriert", "Niedrig", "Mittel", "Hoch"):
        assert word in block
    for api in ("basic", "managed", "embedded", "low", "medium", "high"):
        assert api in block


def test_json_schema_instructions_list_allowed_level_tokens() -> None:
    instr = readiness_explain_json_schema_instructions()
    assert '"basic" | "managed" | "embedded"' in instr or "basic" in instr
    assert "operational_monitoring_explanation" in instr
