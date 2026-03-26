"""Parse LLM JSON for governance maturity Board summary; align; deterministic fallback."""

from __future__ import annotations

import logging
from typing import Any

from app.governance_maturity_contract import (
    EXPLAIN_LIST_ITEM_MAX_CHARS,
    EXPLAIN_LIST_MAX_ITEMS,
    normalize_index_level,
    normalize_readiness_level,
)
from app.governance_maturity_models import GovernanceMaturityResponse
from app.governance_maturity_summary_models import (
    GovernanceMaturityActivitySlice,
    GovernanceMaturityBoardSummaryParseResult,
    GovernanceMaturityOperationalMonitoringSlice,
    GovernanceMaturityOverallAssessment,
    GovernanceMaturityReadinessSlice,
    GovernanceMaturitySummary,
)
from app.services.readiness_explain_structured import extract_json_object

logger = logging.getLogger(__name__)

_PARA_MIN_LEN = 80


def _clamp_str_list(xs: Any, *, max_items: int, max_len: int) -> list[str]:
    if not isinstance(xs, list):
        return []
    out: list[str] = []
    for item in xs[:max_items]:
        s = str(item).strip()[:max_len]
        if s:
            out.append(s)
    return out


def _ord_readiness(level: str) -> int:
    m = {"basic": 0, "managed": 1, "embedded": 2}
    return m.get(str(level).strip().lower(), 0)


def _ord_index(level: str) -> int:
    m = {"low": 0, "medium": 1, "high": 2}
    return m.get(str(level).strip().lower(), 0)


def _index_level_from_ord(o: int) -> str:
    return {0: "low", 1: "medium", 2: "high"}[max(0, min(2, o))]


def conservative_overall_level_from_snapshot(snapshot: GovernanceMaturityResponse) -> str:
    """Pessimistic aggregate (lowest tier wins) across available pillars."""
    ords: list[int] = []
    if snapshot.readiness:
        ords.append(_ord_readiness(snapshot.readiness.level))
    ords.append(_ord_index(snapshot.governance_activity.level))
    oami = snapshot.operational_ai_monitoring
    if oami.status == "active" and oami.level:
        ords.append(_ord_index(str(oami.level)))
    if not ords:
        return "low"
    return _index_level_from_ord(min(ords))


def _coerce_summary_block(data: dict[str, Any]) -> GovernanceMaturitySummary | None:
    raw = data.get("governance_maturity_summary")
    if not isinstance(raw, dict):
        return None
    try:
        return GovernanceMaturitySummary.model_validate(raw)
    except Exception:
        logger.info("governance_maturity_summary_model_validate_failed")
        return None


def _merge_slice_reason(authoritative: str, from_llm: str) -> str:
    llm = (from_llm or "").strip()
    if len(llm) >= 20:
        return llm[:4000]
    return authoritative.strip()[:4000]


def align_governance_maturity_summary_to_snapshot(
    parsed: GovernanceMaturitySummary | None,
    snapshot: GovernanceMaturityResponse,
) -> GovernanceMaturitySummary:
    """Force score/index/level to snapshot; keep LLM narratives when substantive."""
    r_score = 0
    r_level: str = "basic"
    r_interp = "Readiness liegt unter der Schwelle etablierter Steuerung."
    if snapshot.readiness:
        r_score = int(snapshot.readiness.score)
        nl = normalize_readiness_level(snapshot.readiness.level)
        r_level = nl or "basic"
        r_interp = (snapshot.readiness.interpretation or r_interp).strip()

    gai = snapshot.governance_activity
    g_idx = int(gai.index)
    g_lvl = normalize_index_level(gai.level) or "low"

    oami = snapshot.operational_ai_monitoring
    o_idx: int | None
    o_lvl: str | None
    o_default_reason = (
        "Für operatives KI-Monitoring liegen keine ausreichenden Laufzeit-Signale vor."
        if oami.status != "active"
        else (
            oami.message_de
            or "Operatives Monitoring ist eingerichtet; Details siehe Kennzahlen."
        )
    )
    if oami.status == "active" and oami.index is not None and oami.level:
        o_idx = int(oami.index)
        o_lvl = normalize_index_level(str(oami.level)) or str(oami.level)
    else:
        o_idx = None
        o_lvl = None

    pr = parsed.readiness if parsed else None
    pa = parsed.activity if parsed else None
    po = parsed.operational_monitoring if parsed else None
    poa = parsed.overall_assessment if parsed else None

    readiness = GovernanceMaturityReadinessSlice(
        score=r_score,
        level=r_level,  # type: ignore[arg-type]
        short_reason=_merge_slice_reason(
            r_interp,
            pr.short_reason if pr else "",
        ),
    )
    activity = GovernanceMaturityActivitySlice(
        index=g_idx,
        level=g_lvl,  # type: ignore[arg-type]
        short_reason=_merge_slice_reason(
            "Die Nutzung von Steuerungsartefakten in der Plattform spiegelt sich im "
            "Governance-Aktivitätsindex wider.",
            pa.short_reason if pa else "",
        ),
    )
    operational = GovernanceMaturityOperationalMonitoringSlice(
        index=o_idx,
        level=o_lvl,  # type: ignore[arg-type]
        short_reason=_merge_slice_reason(
            o_default_reason,
            po.short_reason if po else "",
        ),
    )

    overall_lvl = conservative_overall_level_from_snapshot(snapshot)
    risks = _clamp_str_list(
        poa.key_risks if poa else [],
        max_items=EXPLAIN_LIST_MAX_ITEMS,
        max_len=EXPLAIN_LIST_ITEM_MAX_CHARS,
    )
    strengths = _clamp_str_list(
        poa.key_strengths if poa else [],
        max_items=EXPLAIN_LIST_MAX_ITEMS,
        max_len=EXPLAIN_LIST_ITEM_MAX_CHARS,
    )
    summary_txt = (poa.short_summary if poa else "").strip()
    if len(summary_txt) < 40:
        summary_txt = (
            "Aus den drei Signalen Readiness, Governance-Aktivität und operativem Monitoring "
            "ergibt sich ein konsolidiertes Lagebild für Aufsicht und Management."
        )

    overall = GovernanceMaturityOverallAssessment(
        level=overall_lvl,  # type: ignore[arg-type]
        short_summary=summary_txt[:4000],
        key_risks=risks,
        key_strengths=strengths,
    )

    return GovernanceMaturitySummary(
        readiness=readiness,
        activity=activity,
        operational_monitoring=operational,
        overall_assessment=overall,
    )


def _fallback_paragraph(summary: GovernanceMaturitySummary) -> str:
    return (
        "Für Aufsicht und Vorstand fasst dieser Bericht die KI-Governance-Reife aus drei "
        "komplementären Blickwinkeln zusammen: struktureller Aufbau, tatsächliche Nutzung der "
        "Steuerungsprozesse und — soweit angebunden — operative Monitoring-Signale im Betrieb. "
        "Die Einordnung dient der Priorisierung von Maßnahmen und ergänzt die nachfolgenden "
        "Kennzahlen und regulatorischen Ausführungen, ohne Einzelfälle oder Personen zu nennen."
    )


def build_fallback_governance_maturity_board_summary_parse_result(
    snapshot: GovernanceMaturityResponse,
) -> GovernanceMaturityBoardSummaryParseResult:
    aligned = align_governance_maturity_summary_to_snapshot(None, snapshot)
    return GovernanceMaturityBoardSummaryParseResult(
        summary=aligned,
        executive_overview_governance_maturity_de=_fallback_paragraph(aligned),
        parse_ok=False,
        used_llm_paragraph=False,
    )


def parse_governance_maturity_board_summary(
    raw_llm_output: str,
    snapshot: GovernanceMaturityResponse,
    *,
    contract_version: str | None = None,
) -> GovernanceMaturityBoardSummaryParseResult:
    """
    Parse LLM output, validate enums, align numeric/level fields to snapshot.

    `contract_version` reserved for future drift checks against prompt version.
    """
    _ = contract_version
    data = extract_json_object(raw_llm_output or "")
    if not data:
        logger.info("governance_maturity_board_summary_json_parse_failed")
        fb = build_fallback_governance_maturity_board_summary_parse_result(snapshot)
        return fb

    paragraph = str(data.get("executive_overview_governance_maturity_de") or "").strip()
    parsed = _coerce_summary_block(data)
    if parsed is None:
        logger.info("governance_maturity_board_summary_missing_or_invalid_block")
        fb = build_fallback_governance_maturity_board_summary_parse_result(snapshot)
        if len(paragraph) >= _PARA_MIN_LEN:
            fb = fb.model_copy(
                update={
                    "executive_overview_governance_maturity_de": paragraph[:8000],
                    "used_llm_paragraph": True,
                },
            )
        return fb.model_copy(update={"parse_ok": False})

    aligned = align_governance_maturity_summary_to_snapshot(parsed, snapshot)
    use_llm_para = len(paragraph) >= _PARA_MIN_LEN
    if not use_llm_para:
        paragraph = _fallback_paragraph(aligned)
    return GovernanceMaturityBoardSummaryParseResult(
        summary=aligned,
        executive_overview_governance_maturity_de=paragraph[:8000],
        parse_ok=True,
        used_llm_paragraph=use_llm_para,
    )


def parse_governance_maturity_summary(
    raw_llm_output: str,
    snapshot: GovernanceMaturityResponse,
    *,
    contract_version: str | None = None,
) -> GovernanceMaturityBoardSummaryParseResult:
    """Alias matching product naming (`governance_maturity_summary`)."""
    return parse_governance_maturity_board_summary(
        raw_llm_output,
        snapshot,
        contract_version=contract_version,
    )
