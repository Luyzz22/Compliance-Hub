"""Guardrails: governance maturity API contract and LLM terminology strings."""

from __future__ import annotations

import json
from pathlib import Path

from app.governance_maturity_contract import (
    GOVERNANCE_MATURITY_CONTRACT_VERSION,
    INDEX_API_LEVELS,
    INDEX_LEVEL_DE,
    READINESS_API_LEVELS,
    READINESS_LEVEL_DE,
    contract_full_mapping_snapshot,
    contract_mapping_for_tests,
    derive_readiness_level_from_score,
    normalize_index_level,
    normalize_readiness_level,
    readiness_explain_json_schema_instructions,
    terminology_contract_for_llm_prompt,
)

_MAPPING_SNAPSHOT_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "governance_maturity_mapping_snapshot.json"
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
    assert "basic" in instr and "managed" in instr and "embedded" in instr
    assert "operational_monitoring_explanation" in instr


def test_contract_mapping_snapshot_stable() -> None:
    snap = contract_mapping_for_tests()
    assert snap["contract_version"] == GOVERNANCE_MATURITY_CONTRACT_VERSION
    assert snap["readiness_api_levels"] == ["basic", "managed", "embedded"]
    assert snap["index_api_levels"] == ["low", "medium", "high"]
    assert snap["readiness_level_de"] == {
        "basic": "Basis",
        "managed": "Etabliert",
        "embedded": "Integriert",
    }
    assert snap["index_level_de"] == {
        "low": "Niedrig",
        "medium": "Mittel",
        "high": "Hoch",
    }


def test_derive_readiness_level_from_score_bands() -> None:
    assert derive_readiness_level_from_score(0) == "basic"
    assert derive_readiness_level_from_score(44) == "basic"
    assert derive_readiness_level_from_score(45) == "managed"
    assert derive_readiness_level_from_score(69) == "managed"
    assert derive_readiness_level_from_score(70) == "embedded"
    assert derive_readiness_level_from_score(100) == "embedded"


def test_governance_maturity_mapping_snapshot_file_matches_contract() -> None:
    """
    Intentional gate: if bands or labels change, update
    tests/fixtures/governance_maturity_mapping_snapshot.json in the same PR.
    """
    from_file = json.loads(_MAPPING_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    live = contract_full_mapping_snapshot()
    assert from_file == live


def test_score_bands_in_full_snapshot_match_derive() -> None:
    snap = contract_full_mapping_snapshot()
    bands = snap["readiness_score_bands"]
    assert isinstance(bands, list) and len(bands) == 3
    for b in bands:
        lo = int(b["score_min"])
        hi_ex = int(b["score_max_exclusive"])
        for s in range(lo, min(hi_ex, 101)):
            assert derive_readiness_level_from_score(s) == b["level"]
