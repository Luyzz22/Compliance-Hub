"""
Golden LLM JSON fixtures: parser + prompt structure regression (no live LLM).

Updating ``tests/fixtures/readiness_explain_golden/*.json`` or the mapping snapshot
must be an intentional review when contract or tone changes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.governance_maturity_contract import (
    GOVERNANCE_MATURITY_CONTRACT_VERSION,
    READINESS_API_LEVELS,
)
from app.readiness_score_models import (
    ReadinessDimensionOut,
    ReadinessScoreDimensions,
    ReadinessScoreResponse,
)
from app.services.readiness_explain_prompt import build_readiness_explain_prompt
from app.services.readiness_explain_structured import (
    parse_and_validate_readiness_explain_response,
    parse_readiness_explain_llm_json,
)

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "readiness_explain_golden"

_READINESS_BLOCK_KEYS = frozenset(
    {
        "score",
        "level",
        "short_reason",
        "drivers_positive",
        "drivers_negative",
        "regulatory_focus",
    },
)
_TOP_KEYS = frozenset({"readiness_explanation", "operational_monitoring_explanation"})


def _snapshot(
    *,
    tenant_id: str,
    score: int,
    level: str,
    interpretation: str = "Statischer Referenztext.",
) -> ReadinessScoreResponse:
    dim = ReadinessDimensionOut
    d = ReadinessScoreDimensions(
        setup=dim(normalized=0.5, score_0_100=50),
        coverage=dim(normalized=0.5, score_0_100=50),
        kpi=dim(normalized=0.5, score_0_100=50),
        gaps=dim(normalized=0.5, score_0_100=50),
        reporting=dim(normalized=0.5, score_0_100=50),
    )
    return ReadinessScoreResponse(
        tenant_id=tenant_id,
        score=score,
        level=level,  # type: ignore[arg-type]
        interpretation=interpretation,
        dimensions=d,
    )


def _load_golden(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("filename", "tenant_id", "score", "level", "reason_substr", "reg_substr"),
    [
        (
            "response_a_basic.json",
            "golden-tenant-a",
            44,
            "basic",
            "Schwelle",
            "EU AI Act",
        ),
        (
            "response_b_managed.json",
            "golden-tenant-b",
            68,
            "managed",
            "Solide strukturelle",
            "ISO 42001",
        ),
        (
            "response_c_embedded.json",
            "golden-tenant-c",
            88,
            "embedded",
            "Hohe strukturelle",
            "Post-Market",
        ),
    ],
)
def test_golden_llm_json_parses_and_aligns_to_snapshot(
    filename: str,
    tenant_id: str,
    score: int,
    level: str,
    reason_substr: str,
    reg_substr: str,
) -> None:
    raw = _load_golden(filename)
    snap = _snapshot(tenant_id=tenant_id, score=score, level=level)
    data = parse_readiness_explain_llm_json(raw)
    assert data is not None
    assert set(data.keys()) == _TOP_KEYS
    re_block = data["readiness_explanation"]
    assert isinstance(re_block, dict)
    assert set(re_block.keys()) <= _READINESS_BLOCK_KEYS
    assert re_block.get("level") in READINESS_API_LEVELS

    out = parse_and_validate_readiness_explain_response(
        raw,
        snapshot=snap,
        oami_index=None,
        oami_level=None,
        has_oami_context=False,
        provider="golden_stub",
        model_id="fixture",
    )
    assert out.readiness_explanation is not None
    assert out.readiness_explanation.score == score
    assert out.readiness_explanation.level == level
    assert reason_substr in out.readiness_explanation.short_reason
    assert reg_substr in out.readiness_explanation.regulatory_focus
    assert out.operational_monitoring_explanation is None
    assert reason_substr in out.explanation or reg_substr in out.explanation


def test_golden_json_whitespace_variants_parse_identically() -> None:
    raw_pretty = _load_golden("response_a_basic.json")
    one_line = json.dumps(json.loads(raw_pretty), ensure_ascii=False, separators=(",", ":"))
    a = parse_readiness_explain_llm_json(raw_pretty)
    b = parse_readiness_explain_llm_json(one_line)
    assert a == b


def test_build_prompt_contains_contract_version_and_tenant_facts() -> None:
    snap = _snapshot(tenant_id="golden-tenant-b", score=68, level="managed")
    envelope = {
        "readiness": snap.model_dump(mode="json"),
        "operational_ai_monitoring": None,
        "governance_activity": None,
    }
    prompt = build_readiness_explain_prompt(facts_envelope=envelope)
    assert GOVERNANCE_MATURITY_CONTRACT_VERSION in prompt
    assert "Explain-Contract-Version" in prompt
    assert "golden-tenant-b" in prompt
    assert "68" in prompt
    assert "managed" in prompt
    for marker in ("Basis", "Etabliert", "Integriert", "readiness_explanation"):
        assert marker in prompt
