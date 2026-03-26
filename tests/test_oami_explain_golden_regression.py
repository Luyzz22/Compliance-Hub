"""
Golden LLM JSON with OAMI block: parser regression (no live LLM).

Updating ``tests/fixtures/oami-explain/*.json`` or the OAMI mapping snapshot
must be an intentional review when contract or bands change.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.governance_maturity_contract import INDEX_API_LEVELS, INDEX_LEVEL_DE
from app.readiness_score_models import (
    ReadinessDimensionOut,
    ReadinessScoreDimensions,
    ReadinessScoreResponse,
)
from app.services.readiness_explain_structured import (
    parse_and_validate_readiness_explain_response,
    parse_readiness_explain_llm_json,
)

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "oami-explain"

_OAMI_BLOCK_KEYS = frozenset(
    {
        "index",
        "level",
        "recent_incidents_summary",
        "monitoring_gaps",
        "improvement_suggestions",
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
    (
        "filename",
        "tenant_id",
        "readiness_score",
        "readiness_level",
        "oami_index",
        "oami_level",
        "oami_summary_substr",
        "readiness_reason_substr",
    ),
    [
        (
            "response_low.json",
            "golden-oami-low",
            44,
            "basic",
            28,
            "low",
            "Kaum belastbare",
            "Schwelle",
        ),
        (
            "response_medium.json",
            "golden-oami-medium",
            68,
            "managed",
            55,
            "medium",
            "Monitoring-Signale",
            "Solide strukturelle",
        ),
        (
            "response_high.json",
            "golden-oami-high",
            88,
            "embedded",
            85,
            "high",
            "Kontinuierliche",
            "Hohe strukturelle",
        ),
    ],
)
def test_oami_golden_llm_json_parses_and_aligns(
    filename: str,
    tenant_id: str,
    readiness_score: int,
    readiness_level: str,
    oami_index: int,
    oami_level: str,
    oami_summary_substr: str,
    readiness_reason_substr: str,
) -> None:
    raw = _load_golden(filename)
    snap = _snapshot(tenant_id=tenant_id, score=readiness_score, level=readiness_level)
    data = parse_readiness_explain_llm_json(raw)
    assert data is not None
    assert set(data.keys()) == _TOP_KEYS
    oami_block = data["operational_monitoring_explanation"]
    assert isinstance(oami_block, dict)
    assert set(oami_block.keys()) <= _OAMI_BLOCK_KEYS
    assert oami_block.get("level") in INDEX_API_LEVELS

    out = parse_and_validate_readiness_explain_response(
        raw,
        snapshot=snap,
        oami_index=oami_index,
        oami_level=oami_level,
        has_oami_context=True,
        provider="golden_stub",
        model_id="fixture",
    )
    assert out.readiness_explanation is not None
    assert out.readiness_explanation.score == readiness_score
    assert out.readiness_explanation.level == readiness_level
    assert out.operational_monitoring_explanation is not None
    o = out.operational_monitoring_explanation
    assert o.index == oami_index
    assert o.level == oami_level
    assert INDEX_LEVEL_DE[oami_level] in ("Niedrig", "Mittel", "Hoch")
    assert oami_summary_substr in o.recent_incidents_summary
    assert readiness_reason_substr in out.explanation


def test_oami_golden_json_whitespace_variants_parse_identically() -> None:
    raw_pretty = _load_golden("response_low.json")
    one_line = json.dumps(json.loads(raw_pretty), ensure_ascii=False, separators=(",", ":"))
    a = parse_readiness_explain_llm_json(raw_pretty)
    b = parse_readiness_explain_llm_json(one_line)
    assert a == b


def test_invalid_oami_level_falls_back_to_server_level() -> None:
    raw = _load_golden("response_medium.json")
    payload = json.loads(raw)
    assert isinstance(payload["operational_monitoring_explanation"], dict)
    payload["operational_monitoring_explanation"]["level"] = "bogus_not_an_api_level"
    raw_bad = json.dumps(payload, ensure_ascii=False)

    snap = _snapshot(tenant_id="golden-oami-invalid", score=68, level="managed")
    out = parse_and_validate_readiness_explain_response(
        raw_bad,
        snapshot=snap,
        oami_index=55,
        oami_level="medium",
        has_oami_context=True,
        provider="golden_stub",
        model_id="fixture",
    )
    assert out.operational_monitoring_explanation is not None
    assert out.operational_monitoring_explanation.level == "medium"


def test_combined_readiness_and_oami_golden_structure_and_de_labels() -> None:
    """End-to-end: same payload carries both blocks; interplay must survive pipeline refactors."""
    raw = _load_golden("response_medium.json")
    snap = _snapshot(tenant_id="golden-combined", score=68, level="managed")
    out = parse_and_validate_readiness_explain_response(
        raw,
        snapshot=snap,
        oami_index=55,
        oami_level="medium",
        has_oami_context=True,
        provider="golden_stub",
        model_id="fixture",
    )
    assert out.readiness_explanation is not None
    re = out.readiness_explanation
    assert re.level == "managed"
    assert "Solide strukturelle" in re.short_reason
    assert out.operational_monitoring_explanation is not None
    oe = out.operational_monitoring_explanation
    assert oe.level == "medium"
    assert INDEX_LEVEL_DE[oe.level] == "Mittel"
    assert isinstance(oe.monitoring_gaps, list) and oe.monitoring_gaps
    assert isinstance(oe.improvement_suggestions, list) and oe.improvement_suggestions
