"""Structured readiness explain: JSON extract, coercion, snapshot alignment."""

from __future__ import annotations

from app.readiness_score_models import (
    ReadinessDimensionOut,
    ReadinessScoreDimensions,
    ReadinessScoreResponse,
)
from app.services.readiness_explain_structured import (
    build_readiness_explain_response_from_llm_text,
    extract_json_object,
)


def _snapshot(*, score: int = 55, level: str = "managed") -> ReadinessScoreResponse:
    dim = ReadinessDimensionOut
    d = ReadinessScoreDimensions(
        setup=dim(normalized=0.5, score_0_100=50),
        coverage=dim(normalized=0.5, score_0_100=50),
        kpi=dim(normalized=0.5, score_0_100=50),
        gaps=dim(normalized=0.5, score_0_100=50),
        reporting=dim(normalized=0.5, score_0_100=50),
    )
    return ReadinessScoreResponse(
        tenant_id="t1",
        score=score,
        level=level,  # type: ignore[arg-type]
        interpretation="Statisch.",
        dimensions=d,
    )


def test_extract_json_object_strips_fence() -> None:
    raw = '```json\n{"a": 1}\n```'
    assert extract_json_object(raw) == {"a": 1}


def test_build_response_aligns_readiness_to_snapshot() -> None:
    snap = _snapshot(score=60, level="embedded")
    llm = """
    {
      "readiness_explanation": {
        "score": 20,
        "level": "basic",
        "short_reason": "Kurz.",
        "drivers_positive": ["a"],
        "drivers_negative": ["b", "c"],
        "regulatory_focus": "EU AI Act"
      },
      "operational_monitoring_explanation": null
    }
    """
    out = build_readiness_explain_response_from_llm_text(
        llm,
        snapshot=snap,
        oami_index=None,
        oami_level=None,
        has_oami_context=False,
        provider="openai",
        model_id="gpt-4o",
    )
    assert out.readiness_explanation is not None
    assert out.readiness_explanation.score == 60
    assert out.readiness_explanation.level == "embedded"
    assert "Kurz." in out.explanation


def test_oami_struct_coerced_when_context_present() -> None:
    snap = _snapshot()
    llm = """
    {
      "readiness_explanation": {
        "score": 55,
        "level": "managed",
        "short_reason": "R",
        "drivers_positive": [],
        "drivers_negative": [],
        "regulatory_focus": ""
      },
      "operational_monitoring_explanation": {
        "index": 40,
        "level": "medium",
        "recent_incidents_summary": "",
        "monitoring_gaps": ["g1"],
        "improvement_suggestions": ["s1"]
      }
    }
    """
    out = build_readiness_explain_response_from_llm_text(
        llm,
        snapshot=snap,
        oami_index=40,
        oami_level="medium",
        has_oami_context=True,
        provider="x",
        model_id="y",
    )
    assert out.operational_monitoring_explanation is not None
    assert out.operational_monitoring_explanation.level == "medium"
