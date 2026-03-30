"""Parse und Align für Advisor Governance-Maturity-Brief (JSON)."""

from __future__ import annotations

import logging
from typing import Any

from app.advisor_governance_maturity_brief_models import (
    AdvisorGovernanceMaturityBrief,
    AdvisorGovernanceMaturityBriefParseResult,
)
from app.governance_maturity_models import GovernanceMaturityResponse
from app.governance_maturity_summary_models import GovernanceMaturitySummary
from app.llm.exceptions import LLMContractViolation
from app.llm.guardrails import validate_llm_json_output
from app.services.governance_maturity_summary_parse import (
    align_governance_maturity_summary_to_snapshot,
)
from app.services.readiness_explain_structured import extract_json_object

logger = logging.getLogger(__name__)

_CLIENT_PARA_MIN_LEN = 20


def _coerce_summary(data: dict[str, Any]) -> GovernanceMaturitySummary | None:
    raw = data.get("governance_maturity_summary")
    if not isinstance(raw, dict):
        return None
    try:
        return GovernanceMaturitySummary.model_validate(raw)
    except Exception:
        logger.info("advisor_governance_maturity_brief_summary_validate_failed")
        return None


def build_fallback_advisor_governance_maturity_brief_parse_result(
    snapshot: GovernanceMaturityResponse,
) -> AdvisorGovernanceMaturityBriefParseResult:
    """Deterministischer Brief ohne LLM: aligned summary + heuristische Fokusliste."""
    aligned = align_governance_maturity_summary_to_snapshot(None, snapshot)
    focus: list[str] = []
    if aligned.readiness.level == "basic":
        focus.append("Readiness niedrig – Register, Rollen und Nachweise priorisieren.")
    elif aligned.readiness.level == "managed":
        focus.append("Readiness „managed“ – verbleibende Lücken bei High-Risk-Systemen schließen.")
    if aligned.activity.level == "low":
        focus.append("GAI niedrig – Steuerungsartefakte und dokumentierte Nutzung ausbauen.")
    om = aligned.operational_monitoring
    if om.level is None or (om.level and str(om.level) == "low"):
        focus.append("OAMI niedrig – Monitoring und belastbare Laufzeit-Signale ausbauen.")
    if not focus:
        focus.append(
            "Niveau halten – Monitoring und Berichtswesen im gewohnten Rhythmus fortführen.",
        )
    brief = AdvisorGovernanceMaturityBrief(
        governance_maturity_summary=aligned,
        recommended_focus_areas=focus,
        suggested_next_steps_window="nächste 90 Tage",
        client_ready_paragraph_de=None,
    )
    return AdvisorGovernanceMaturityBriefParseResult(
        brief=brief,
        parse_ok=False,
        used_llm_client_paragraph=False,
    )


def parse_advisor_governance_maturity_brief(
    raw_llm_output: str,
    snapshot: GovernanceMaturityResponse,
    *,
    contract_version: str | None = None,
) -> AdvisorGovernanceMaturityBriefParseResult:
    _ = contract_version
    data = extract_json_object(raw_llm_output or "")
    if not data:
        logger.info("advisor_governance_maturity_brief_json_parse_failed")
        return build_fallback_advisor_governance_maturity_brief_parse_result(snapshot)

    parsed = _coerce_summary(data)
    if parsed is None:
        logger.info("advisor_governance_maturity_brief_missing_summary")
        return build_fallback_advisor_governance_maturity_brief_parse_result(snapshot)

    aligned_summary = align_governance_maturity_summary_to_snapshot(parsed, snapshot)

    window = str(data.get("suggested_next_steps_window") or "").strip() or "nächste 90 Tage"
    raw_focus = data.get("recommended_focus_areas")
    focus_list: list[str] = []
    if isinstance(raw_focus, list):
        for item in raw_focus:
            s = str(item).strip()
            if s:
                focus_list.append(s)

    para_raw = data.get("client_ready_paragraph_de")
    para: str | None = None
    use_llm_para = False
    if para_raw is not None and str(para_raw).strip():
        p = str(para_raw).strip()[:600]
        if len(p) >= _CLIENT_PARA_MIN_LEN:
            para = p
            use_llm_para = True

    payload: dict[str, Any] = {
        "governance_maturity_summary": aligned_summary.model_dump(mode="json"),
        "recommended_focus_areas": focus_list,
        "suggested_next_steps_window": window[:120],
        "client_ready_paragraph_de": para,
    }
    try:
        brief = validate_llm_json_output(payload, AdvisorGovernanceMaturityBrief)
    except LLMContractViolation:
        logger.info("advisor_governance_maturity_brief_contract_validation_failed")
        return build_fallback_advisor_governance_maturity_brief_parse_result(snapshot)

    return AdvisorGovernanceMaturityBriefParseResult(
        brief=brief,
        parse_ok=True,
        used_llm_client_paragraph=use_llm_para,
    )
