"""Preset service layer — anti-corruption boundary for enterprise callers.

This module is the single entry point for all preset invocations. It:
- Maps external preset inputs to internal AdvisorRequest
- Runs the generic advisor agent via run_advisor()
- Derives GRC-specific fields from the advisor response
- Builds the enterprise PresetResult with separated human/machine/grc
- Tags evidence events with flow_type, client_id, system_id
- Enforces per-preset SLA timeouts

REST controllers, Temporal workflows, and future SAP/DATEV connectors
should all call these functions — never the raw advisor agent directly.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.advisor.channels import ChannelMetadata
from app.advisor.errors import ADVISOR_SLA_TIMEOUT_SECONDS
from app.advisor.preset_models import (
    RESPONSE_CONTRACT_VERSION,
    AiActRiskGrc,
    AiActRiskPresetInput,
    Iso42001GapCheckPresetInput,
    Iso42001GapGrc,
    Nis2ObligationsGrc,
    Nis2ObligationsPresetInput,
    PresetHumanReadable,
    PresetInputBase,
    PresetMachineReadable,
    PresetResponseMeta,
    PresetResult,
)
from app.advisor.presets import (
    EU_AI_ACT_RISK_EXTRA_TAGS,
    ISO42001_GAP_EXTRA_TAGS,
    NIS2_OBLIGATIONS_EXTRA_TAGS,
    FlowType,
    build_eu_ai_act_risk_query,
    build_iso42001_gap_query,
    build_nis2_obligations_query,
)
from app.advisor.response_models import AdvisorStructuredResponse
from app.advisor.service import AdvisorRequest, run_advisor

logger = logging.getLogger(__name__)

PRESET_SLA_TIMEOUTS: dict[FlowType, float] = {
    FlowType.eu_ai_act_risk_assessment: 45.0,
    FlowType.nis2_obligations: ADVISOR_SLA_TIMEOUT_SECONDS,
    FlowType.iso42001_gap_check: 45.0,
}


# ---------------------------------------------------------------------------
# Public API — one function per preset
# ---------------------------------------------------------------------------


def run_eu_ai_act_risk_preset(
    inp: AiActRiskPresetInput,
    agent: Any = None,
) -> PresetResult:
    """EU AI Act high-risk classification preset.

    Builds a German-language query from the structured input, runs it
    through the advisor agent, then derives GRC risk fields from the
    response.
    """
    from app.advisor.presets import EuAiActRiskAssessmentInput

    legacy = EuAiActRiskAssessmentInput(
        use_case_description=inp.use_case_description,
        industry_sector=inp.industry_sector,
        intended_purpose=inp.intended_purpose,
    )
    query = build_eu_ai_act_risk_query(legacy)

    raw = _run_preset_core(
        flow_type=FlowType.eu_ai_act_risk_assessment,
        query=query,
        inp=inp,
        extra_tags=EU_AI_ACT_RISK_EXTRA_TAGS,
        agent=agent,
    )

    grc = _derive_ai_act_risk_grc(raw, inp)
    return _build_preset_result(
        raw,
        inp,
        FlowType.eu_ai_act_risk_assessment,
        grc.model_dump(),
    )


def run_nis2_obligations_preset(
    inp: Nis2ObligationsPresetInput,
    agent: Any = None,
) -> PresetResult:
    """NIS2 obligation mapping preset."""
    from app.advisor.presets import Nis2ObligationsInput

    legacy = Nis2ObligationsInput(
        entity_role=inp.entity_role,
        sector=inp.sector,
        employee_count=inp.employee_count,
    )
    query = build_nis2_obligations_query(legacy)

    raw = _run_preset_core(
        flow_type=FlowType.nis2_obligations,
        query=query,
        inp=inp,
        extra_tags=NIS2_OBLIGATIONS_EXTRA_TAGS,
        agent=agent,
    )

    grc = _derive_nis2_grc(raw, inp)
    return _build_preset_result(
        raw,
        inp,
        FlowType.nis2_obligations,
        grc.model_dump(),
    )


def run_iso42001_gap_preset(
    inp: Iso42001GapCheckPresetInput,
    agent: Any = None,
) -> PresetResult:
    """ISO 42001 gap analysis preset."""
    from app.advisor.presets import Iso42001GapCheckInput

    legacy = Iso42001GapCheckInput(
        current_measures=inp.current_measures,
        ai_system_count=inp.ai_system_count,
    )
    query = build_iso42001_gap_query(legacy)

    raw = _run_preset_core(
        flow_type=FlowType.iso42001_gap_check,
        query=query,
        inp=inp,
        extra_tags=ISO42001_GAP_EXTRA_TAGS,
        agent=agent,
    )

    grc = _derive_iso42001_grc(raw, inp)
    return _build_preset_result(
        raw,
        inp,
        FlowType.iso42001_gap_check,
        grc.model_dump(),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_or_create_agent(agent: Any) -> Any:
    if agent is not None:
        return agent
    from app.services.agents.advisor_compliance_agent import AdvisorComplianceAgent
    from app.services.rag.config import RAGConfig
    from app.services.rag.corpus_loader import load_advisor_corpus
    from app.services.rag.hybrid_retriever import HybridRetriever

    corpus = load_advisor_corpus()
    config = RAGConfig()
    retriever = HybridRetriever(corpus, config)
    return AdvisorComplianceAgent(retriever=retriever)


def _run_preset_core(
    *,
    flow_type: FlowType,
    query: str,
    inp: PresetInputBase,
    extra_tags: list[str],
    agent: Any = None,
) -> AdvisorStructuredResponse:
    """Map preset input → AdvisorRequest → run_advisor()."""
    ctx = inp.context
    if not ctx.tenant_id and inp.tenant_id:
        ctx.tenant_id = inp.tenant_id
    cm = inp.channel_metadata or ChannelMetadata()
    if ctx.client_id and not cm.datev_client_number:
        cm.datev_client_number = ctx.client_id

    request = AdvisorRequest(
        query=query,
        tenant_id=inp.effective_tenant_id(),
        channel=inp.channel,
        channel_metadata=cm,
        request_id=inp.request_id,
        trace_id=inp.trace_id,
        flow_type=flow_type.value,
        extra_tags=extra_tags,
        client_id=ctx.client_id,
        system_id=ctx.system_id,
    )

    resolved_agent = _get_or_create_agent(agent)
    timeout = PRESET_SLA_TIMEOUTS.get(flow_type, ADVISOR_SLA_TIMEOUT_SECONDS)
    return run_advisor(request, resolved_agent, timeout_seconds=timeout)


def _build_preset_result(
    raw: AdvisorStructuredResponse,
    inp: PresetInputBase,
    flow_type: FlowType,
    grc_fields: dict[str, Any],
) -> PresetResult:
    ref_ids = dict(raw.ref_ids)
    ctx = inp.context
    if ctx.client_id:
        ref_ids["client_id"] = ctx.client_id
    if ctx.system_id:
        ref_ids["system_id"] = ctx.system_id

    return PresetResult(
        human=PresetHumanReadable(
            answer_de=raw.answer,
            is_escalated=raw.is_escalated,
            escalation_reason=raw.escalation_reason,
            confidence_level=raw.confidence_level,
        ),
        machine=PresetMachineReadable(
            tags=raw.tags,
            suggested_next_steps=raw.suggested_next_steps,
            ref_ids=ref_ids,
            intent=raw.intent,
        ),
        grc=grc_fields,
        meta=PresetResponseMeta(
            version=RESPONSE_CONTRACT_VERSION,
            flow_type=flow_type.value,
            channel=inp.channel,
            channel_metadata=inp.channel_metadata,
            request_id=inp.request_id,
            trace_id=inp.trace_id,
            latency_ms=raw.meta.latency_ms,
            is_cached=raw.meta.is_cached,
            context=ctx,
        ),
        error=raw.error,
        needs_manual_followup=raw.needs_manual_followup,
        agent_trace=raw.agent_trace,
    )


# ---------------------------------------------------------------------------
# GRC field derivation (heuristic, from answer text + tags)
# ---------------------------------------------------------------------------

_HIGH_RISK_SIGNALS = re.compile(
    r"hochrisiko|high.risk|anhang\s*iii|annex\s*iii",
    re.IGNORECASE,
)
_LIMITED_RISK_SIGNALS = re.compile(
    r"begrenztes\s*risiko|limited.risk|transparenzpflicht",
    re.IGNORECASE,
)
_MINIMAL_RISK_SIGNALS = re.compile(
    r"minimales?\s*risiko|minimal.risk|kein\s*hochrisiko|nicht.*hochrisiko",
    re.IGNORECASE,
)

_USE_CASE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"kredit|bonität|scoring", re.IGNORECASE), "credit_scoring"),
    (re.compile(r"recruit|personal|bewerbung", re.IGNORECASE), "recruitment"),
    (re.compile(r"biometr", re.IGNORECASE), "biometric_identification"),
    (re.compile(r"medizin|diagnos|gesundheit", re.IGNORECASE), "medical_device"),
    (re.compile(r"autonom|fahrzeug|vehicle", re.IGNORECASE), "autonomous_systems"),
    (re.compile(r"überwach|surveillance|monitor", re.IGNORECASE), "surveillance"),
]

_ANNEX_III_PATTERN = re.compile(
    r"anhang\s*iii[^.]{0,80}(?:nr\.?\s*|kategorie\s*)(\d+)",
    re.IGNORECASE,
)


def _derive_ai_act_risk_grc(
    raw: AdvisorStructuredResponse,
    inp: AiActRiskPresetInput,
) -> AiActRiskGrc:
    combined = f"{inp.use_case_description} {raw.answer}"

    if _HIGH_RISK_SIGNALS.search(raw.answer):
        likelihood = "likely"
        risk_cat = "high_risk"
    elif _MINIMAL_RISK_SIGNALS.search(raw.answer):
        likelihood = "unlikely"
        risk_cat = "minimal_risk"
    elif _LIMITED_RISK_SIGNALS.search(raw.answer):
        likelihood = "unclear"
        risk_cat = "limited_risk"
    else:
        likelihood = "unknown"
        risk_cat = "unclassified"

    use_case_type = ""
    for pat, uct in _USE_CASE_PATTERNS:
        if pat.search(combined):
            use_case_type = uct
            break

    annex_match = _ANNEX_III_PATTERN.search(raw.answer)
    annex_cat = annex_match.group(0).strip() if annex_match else ""

    conformity = None
    if risk_cat == "high_risk":
        conformity = True
    elif risk_cat in ("minimal_risk", "limited_risk"):
        conformity = False

    return AiActRiskGrc(
        risk_category=risk_cat,
        use_case_type=use_case_type,
        high_risk_likelihood=likelihood,
        annex_iii_category=annex_cat,
        conformity_assessment_required=conformity,
    )


_ENTITY_TYPE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"wesentlich|essential", re.IGNORECASE), "essential"),
    (re.compile(r"wichtig|important", re.IGNORECASE), "important"),
]

_OBLIGATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"meldepflicht|incident.report|frühwarnung", re.IGNORECASE), "incident_reporting"),
    (re.compile(r"risikomanagement|risk.management", re.IGNORECASE), "risk_management"),
    (re.compile(r"lieferkette|supply.chain", re.IGNORECASE), "supply_chain"),
    (re.compile(r"bcm|business.continuity|kontinuität", re.IGNORECASE), "bcm"),
    (re.compile(r"governance|leitungsorgan", re.IGNORECASE), "governance"),
    (re.compile(r"registrierung|registration", re.IGNORECASE), "registration"),
]

_DEADLINE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"24\s*(?:stunden|h).*(?:früh|early)", re.IGNORECASE), "24h_early_warning"),
    (re.compile(r"72\s*(?:stunden|h)", re.IGNORECASE), "72h_notification"),
    (re.compile(r"abschlussbericht|final.report", re.IGNORECASE), "final_report"),
]


def _derive_nis2_grc(
    raw: AdvisorStructuredResponse,
    inp: Nis2ObligationsPresetInput,
) -> Nis2ObligationsGrc:
    combined = f"{inp.entity_role} {raw.answer}"

    entity_type = ""
    for pat, et in _ENTITY_TYPE_PATTERNS:
        if pat.search(combined):
            entity_type = et
            break

    obligations: list[str] = []
    for pat, tag in _OBLIGATION_PATTERNS:
        if pat.search(combined):
            obligations.append(tag)

    deadlines: list[str] = []
    for pat, dl in _DEADLINE_PATTERNS:
        if pat.search(raw.answer):
            deadlines.append(dl)

    return Nis2ObligationsGrc(
        nis2_entity_type=entity_type,
        obligation_tags=sorted(set(obligations)),
        reporting_deadlines=sorted(set(deadlines)),
    )


_CONTROL_FAMILY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"governance|verantwort|leitung", re.IGNORECASE), "governance"),
    (re.compile(r"risiko|risk", re.IGNORECASE), "risk"),
    (re.compile(r"daten|data", re.IGNORECASE), "data"),
    (re.compile(r"monitor|überwach", re.IGNORECASE), "monitoring"),
    (re.compile(r"lebenszyklus|lifecycle", re.IGNORECASE), "lifecycle"),
    (re.compile(r"transparenz|transparency|erklär", re.IGNORECASE), "transparency"),
]

_GAP_SEVERITY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"kritisch|critical|schwerwiegend", re.IGNORECASE), "critical"),
    (re.compile(r"erheblich|major|wesentlich", re.IGNORECASE), "major"),
    (re.compile(r"gering|minor|klein", re.IGNORECASE), "minor"),
]


def _derive_iso42001_grc(
    raw: AdvisorStructuredResponse,
    inp: Iso42001GapCheckPresetInput,
) -> Iso42001GapGrc:
    combined = f"{inp.current_measures} {raw.answer}"

    families: list[str] = []
    for pat, fam in _CONTROL_FAMILY_PATTERNS:
        if pat.search(raw.answer):
            families.append(fam)

    severity = "unknown"
    for pat, sev in _GAP_SEVERITY_PATTERNS:
        if pat.search(raw.answer):
            severity = sev
            break

    iso27001_overlap = None
    if re.search(r"iso\s*27001", combined, re.IGNORECASE):
        iso27001_overlap = True

    return Iso42001GapGrc(
        control_families=sorted(set(families)),
        gap_severity=severity,
        iso27001_overlap=iso27001_overlap,
    )
