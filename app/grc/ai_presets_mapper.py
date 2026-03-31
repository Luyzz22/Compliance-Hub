"""Maps advisor preset results to GRC entities.

Takes a PresetResult + EnterpriseContext and produces one or more
GRC entity instances (risk, obligation, gap). Handles idempotent
upsert, AI System inventory linking, and evidence logging.

Only creates records for successful, non-escalated preset runs.
Escalated / policy-refused results are skipped — those need human
review before becoming formal GRC artefacts.

When a system_id is present the mapper ensures a corresponding
AiSystem inventory record exists (auto-creating a minimal stub if
needed) and links the GRC record to it.
"""

from __future__ import annotations

import logging

from app.advisor.enterprise_context import EnterpriseContext
from app.advisor.preset_models import PresetResult
from app.advisor.presets import FlowType
from app.grc.models import (
    AiRiskAssessment,
    AiSystemClassification,
    Iso42001GapRecord,
    Nis2ObligationRecord,
)
from app.grc.store import (
    get_or_create_ai_system,
    upsert_ai_system,
    upsert_gap,
    upsert_nis2,
    upsert_risk,
)
from app.services.rag.evidence_store import record_event

logger = logging.getLogger(__name__)


def map_preset_to_grc(
    flow_type: FlowType,
    result: PresetResult,
    context: EnterpriseContext,
    *,
    input_summary: str = "",
) -> str | None:
    """Create/update GRC record from a preset result.

    Returns the GRC record ID on success, None if skipped.
    Skips creation for escalated, errored, or low-confidence results
    that need human review.
    """
    if result.error is not None:
        logger.info("grc_skip_error", extra={"flow_type": flow_type})
        return None
    if result.human.is_escalated:
        logger.info("grc_skip_escalated", extra={"flow_type": flow_type})
        return None
    if result.needs_manual_followup:
        logger.info("grc_skip_manual_followup", extra={"flow_type": flow_type})
        return None

    ai_system_id = _ensure_ai_system(context, flow_type, result)

    trace_id = result.meta.trace_id or ""
    request_id = result.meta.request_id or ""

    if flow_type == FlowType.eu_ai_act_risk_assessment:
        record_id = _map_ai_act_risk(result, context, trace_id, request_id)
    elif flow_type == FlowType.nis2_obligations:
        record_id = _map_nis2(result, context, trace_id, request_id, input_summary)
    elif flow_type == FlowType.iso42001_gap_check:
        record_id = _map_iso42001(result, context, trace_id, request_id, input_summary)
    else:
        logger.warning("grc_unknown_flow_type", extra={"flow_type": flow_type})
        return None

    _log_grc_evidence_event(
        flow_type,
        record_id,
        context,
        trace_id,
        ai_system_id=ai_system_id,
    )
    return record_id


# ---------------------------------------------------------------------------
# AI System linking (Wave 11)
# ---------------------------------------------------------------------------


def _ensure_ai_system(
    ctx: EnterpriseContext,
    flow_type: FlowType,
    result: PresetResult,
) -> str | None:
    """Ensure an AiSystem record exists for the given context.

    If ``system_id`` is empty no inventory record is needed.
    For risk assessments that signal high-risk, the classification is set
    to ``high_risk_candidate`` — never ``high_risk`` (human decision).
    For NIS2 presets the ``nis2_relevant`` flag is set.
    For ISO 42001 presets the ``iso42001_in_scope`` flag is set.
    """
    if not ctx.system_id:
        return None

    ai_sys = get_or_create_ai_system(
        tenant_id=ctx.tenant_id,
        system_id=ctx.system_id,
        client_id=ctx.client_id,
    )

    updated = False

    if flow_type == FlowType.eu_ai_act_risk_assessment:
        risk_cat = result.grc.get("risk_category", "")
        if risk_cat in ("high_risk",) and ai_sys.ai_act_classification not in (
            AiSystemClassification.high_risk,
            AiSystemClassification.high_risk_candidate,
        ):
            ai_sys.ai_act_classification = AiSystemClassification.high_risk_candidate
            updated = True
        elif (
            risk_cat == "limited_risk"
            and ai_sys.ai_act_classification == AiSystemClassification.not_in_scope
        ):
            ai_sys.ai_act_classification = AiSystemClassification.limited
            updated = True
        elif (
            risk_cat == "minimal_risk"
            and ai_sys.ai_act_classification == AiSystemClassification.not_in_scope
        ):
            ai_sys.ai_act_classification = AiSystemClassification.minimal
            updated = True

    if flow_type == FlowType.nis2_obligations and not ai_sys.nis2_relevant:
        ai_sys.nis2_relevant = True
        updated = True

    if flow_type == FlowType.iso42001_gap_check and not ai_sys.iso42001_in_scope:
        ai_sys.iso42001_in_scope = True
        updated = True

    if updated:
        upsert_ai_system(ai_sys)

    return ai_sys.id


# ---------------------------------------------------------------------------
# Per-preset mappers
# ---------------------------------------------------------------------------


def _map_ai_act_risk(
    result: PresetResult,
    ctx: EnterpriseContext,
    trace_id: str,
    request_id: str,
) -> str:
    grc = result.grc
    record = AiRiskAssessment(
        tenant_id=ctx.tenant_id,
        client_id=ctx.client_id,
        system_id=ctx.system_id,
        risk_category=grc.get("risk_category", "unclassified"),
        use_case_type=grc.get("use_case_type", ""),
        high_risk_likelihood=grc.get("high_risk_likelihood", "unknown"),
        annex_iii_category=grc.get("annex_iii_category", ""),
        conformity_assessment_required=grc.get("conformity_assessment_required"),
        source_event_id=request_id,
        source_trace_id=trace_id,
        tags=result.machine.tags,
        suggested_next_steps=result.machine.suggested_next_steps,
    )
    persisted = upsert_risk(record)
    return persisted.id


def _map_nis2(
    result: PresetResult,
    ctx: EnterpriseContext,
    trace_id: str,
    request_id: str,
    input_summary: str,
) -> str:
    grc = result.grc
    record = Nis2ObligationRecord(
        tenant_id=ctx.tenant_id,
        client_id=ctx.client_id,
        system_id=ctx.system_id,
        nis2_entity_type=grc.get("nis2_entity_type", ""),
        obligation_tags=grc.get("obligation_tags", []),
        reporting_deadlines=grc.get("reporting_deadlines", []),
        entity_role=input_summary,
        source_event_id=request_id,
        source_trace_id=trace_id,
        tags=result.machine.tags,
        suggested_next_steps=result.machine.suggested_next_steps,
    )
    persisted = upsert_nis2(record)
    return persisted.id


def _map_iso42001(
    result: PresetResult,
    ctx: EnterpriseContext,
    trace_id: str,
    request_id: str,
    input_summary: str,
) -> str:
    grc = result.grc
    record = Iso42001GapRecord(
        tenant_id=ctx.tenant_id,
        client_id=ctx.client_id,
        system_id=ctx.system_id,
        control_families=grc.get("control_families", []),
        gap_severity=grc.get("gap_severity", "unknown"),
        iso27001_overlap=grc.get("iso27001_overlap"),
        current_measures_summary=input_summary[:500] if input_summary else "",
        source_event_id=request_id,
        source_trace_id=trace_id,
        tags=result.machine.tags,
        suggested_next_steps=result.machine.suggested_next_steps,
    )
    persisted = upsert_gap(record)
    return persisted.id


# ---------------------------------------------------------------------------
# Evidence linking
# ---------------------------------------------------------------------------


def _log_grc_evidence_event(
    flow_type: FlowType,
    record_id: str,
    ctx: EnterpriseContext,
    trace_id: str,
    *,
    ai_system_id: str | None = None,
) -> None:
    """Record an evidence event linking the advisor run to the GRC artefact."""
    payload: dict[str, str] = {
        "event_type": "grc_record_created",
        "tenant_id": ctx.tenant_id,
        "grc_record_id": record_id,
        "flow_type": flow_type.value,
        "trace_id": trace_id,
        **ctx.evidence_dict(),
    }
    if ai_system_id:
        payload["ai_system_id"] = ai_system_id
    record_event(payload)
    logger.info("grc_evidence_linked", extra=payload)
