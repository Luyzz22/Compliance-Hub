"""Parse and validate structured JSON from readiness-score LLM; compose legacy explanation text."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.governance_maturity_contract import (
    normalize_index_level,
    normalize_readiness_level,
)
from app.readiness_score_models import (
    OperationalMonitoringExplanationStructured,
    ReadinessExplanationStructured,
    ReadinessScoreExplainResponse,
    ReadinessScoreResponse,
)

logger = logging.getLogger(__name__)


def _strip_json_fence(raw: str) -> str:
    t = raw.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```\s*$", "", t)
    return t.strip()


def extract_json_object(raw: str) -> dict[str, Any] | None:
    """Best-effort: fenced JSON, or first {...} block."""
    t = _strip_json_fence(raw)
    try:
        data = json.loads(t)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    start = t.find("{")
    end = t.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(t[start : end + 1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _clamp_str_list(xs: Any, *, max_items: int, max_len: int) -> list[str]:
    if not isinstance(xs, list):
        return []
    out: list[str] = []
    for item in xs[:max_items]:
        s = str(item).strip()[:max_len]
        if s:
            out.append(s)
    return out


def _coerce_readiness_struct(
    data: dict[str, Any],
    snapshot: ReadinessScoreResponse,
) -> ReadinessExplanationStructured | None:
    block = data.get("readiness_explanation")
    if not isinstance(block, dict):
        return None
    level_raw = block.get("level")
    level = normalize_readiness_level(level_raw) or snapshot.level
    score_raw = block.get("score", snapshot.score)
    try:
        score = int(score_raw)
    except (TypeError, ValueError):
        score = snapshot.score
    score = max(0, min(100, score))
    return ReadinessExplanationStructured(
        score=score,
        level=level,
        short_reason=str(block.get("short_reason") or "")[:4000],
        drivers_positive=_clamp_str_list(block.get("drivers_positive"), max_items=8, max_len=500),
        drivers_negative=_clamp_str_list(block.get("drivers_negative"), max_items=8, max_len=500),
        regulatory_focus=str(block.get("regulatory_focus") or "")[:2000],
    )


def _coerce_oami_struct(
    data: dict[str, Any],
    *,
    default_index: int | None,
    default_level: str | None,
) -> OperationalMonitoringExplanationStructured | None:
    block = data.get("operational_monitoring_explanation")
    if block is None:
        return None
    if not isinstance(block, dict):
        return None
    idx_raw = block.get("index", default_index)
    index: int | None
    try:
        if idx_raw is None:
            index = default_index
        else:
            index = max(0, min(100, int(idx_raw)))
    except (TypeError, ValueError):
        index = default_index

    lvl = normalize_index_level(block.get("level", default_level))
    if lvl is None and default_level:
        lvl = normalize_index_level(default_level)

    return OperationalMonitoringExplanationStructured(
        index=index,
        level=lvl,
        recent_incidents_summary=str(block.get("recent_incidents_summary") or "")[:2000],
        monitoring_gaps=_clamp_str_list(block.get("monitoring_gaps"), max_items=8, max_len=500),
        improvement_suggestions=_clamp_str_list(
            block.get("improvement_suggestions"),
            max_items=8,
            max_len=500,
        ),
    )


def compose_legacy_explanation_text(
    readiness: ReadinessExplanationStructured,
    oami: OperationalMonitoringExplanationStructured | None,
) -> str:
    """Single block for clients that only render `explanation` (no structured UI)."""
    parts: list[str] = []
    if readiness.short_reason.strip():
        parts.append(readiness.short_reason.strip())
    if readiness.drivers_negative:
        block = ["Priorisierte Maßnahmen (Auszug):"] + [
            f"{i}. {d}" for i, d in enumerate(readiness.drivers_negative[:3], start=1)
        ]
        parts.append("\n".join(block))
    if oami and (oami.improvement_suggestions or oami.monitoring_gaps):
        xs = oami.improvement_suggestions or oami.monitoring_gaps
        block = ["Operatives Monitoring (OAMI):"] + [f"- {s}" for s in xs[:3]]
        parts.append("\n".join(block))
    return "\n\n".join(parts).strip()


def build_readiness_explain_response_from_llm_text(
    llm_text: str,
    *,
    snapshot: ReadinessScoreResponse,
    oami_index: int | None,
    oami_level: str | None,
    has_oami_context: bool,
    provider: str,
    model_id: str,
) -> ReadinessScoreExplainResponse:
    data = extract_json_object(llm_text)
    if not data:
        logger.info("readiness_explain_json_parse_failed; using raw text")
        return ReadinessScoreExplainResponse(
            explanation=(llm_text or "").strip(),
            provider=provider,
            model_id=model_id,
            readiness_explanation=None,
            operational_monitoring_explanation=None,
        )

    r_struct = _coerce_readiness_struct(data, snapshot)
    o_struct: OperationalMonitoringExplanationStructured | None = None
    if has_oami_context:
        o_struct = _coerce_oami_struct(
            data,
            default_index=oami_index,
            default_level=oami_level,
        )
        if o_struct is not None and o_struct.level is None and oami_level:
            o_struct = o_struct.model_copy(
                update={"level": normalize_index_level(oami_level)},
            )

    if r_struct is None:
        return ReadinessScoreExplainResponse(
            explanation=(llm_text or "").strip(),
            provider=provider,
            model_id=model_id,
            readiness_explanation=None,
            operational_monitoring_explanation=o_struct,
        )

    # Align score/level with server truth if model drifted
    r_aligned = r_struct.model_copy(
        update={"score": snapshot.score, "level": snapshot.level},
    )
    narrative = compose_legacy_explanation_text(r_aligned, o_struct)
    if not narrative:
        narrative = (snapshot.interpretation or "").strip() or (llm_text or "").strip()

    return ReadinessScoreExplainResponse(
        explanation=narrative,
        provider=provider,
        model_id=model_id,
        readiness_explanation=r_aligned,
        operational_monitoring_explanation=o_struct,
    )
