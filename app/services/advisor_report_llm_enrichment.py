"""Optional LLM-Formulierung für Advisor-Steckbrief (nur aus strukturierten Kennzahlen)."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.advisor_models import AdvisorTenantReport
from app.feature_flags import FeatureFlag, is_feature_enabled
from app.llm.guardrails import log_input_guardrail_scan, scan_input_for_pii_and_injection
from app.llm_models import LLMTaskType
from app.services.advisor_governance_maturity_brief_llm import (
    maybe_build_advisor_governance_maturity_brief_result,
)
from app.services.llm_router import LLMRouter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _deterministic_facts_payload(report: AdvisorTenantReport) -> dict:
    return {
        "tenant_id": report.tenant_id,
        "tenant_name": report.tenant_name,
        "ai_systems_total": report.ai_systems_total,
        "high_risk_systems_count": report.high_risk_systems_count,
        "high_risk_with_full_controls_count": report.high_risk_with_full_controls_count,
        "eu_ai_act_readiness_score": report.eu_ai_act_readiness_score,
        "eu_ai_act_deadline": report.eu_ai_act_deadline,
        "eu_ai_act_days_remaining": report.eu_ai_act_days_remaining,
        "nis2_incident_readiness_percent": report.nis2_incident_readiness_percent,
        "nis2_supplier_risk_coverage_percent": report.nis2_supplier_risk_coverage_percent,
        "nis2_ot_it_segregation_mean_percent": report.nis2_ot_it_segregation_mean_percent,
        "nis2_critical_focus_systems_count": report.nis2_critical_focus_systems_count,
        "governance_open_actions_count": report.governance_open_actions_count,
        "governance_overdue_actions_count": report.governance_overdue_actions_count,
        "top_critical_requirements": [c.model_dump() for c in report.top_critical_requirements],
        "setup_completed_steps": report.setup_completed_steps,
        "setup_total_steps": report.setup_total_steps,
        "setup_open_step_labels": list(report.setup_open_step_labels),
        "risiko_nis2_entity_category": report.risiko_nis2_entity_category,
        "risiko_kritis_sector_label_de": report.risiko_kritis_sector_label_de,
        "risiko_incidents_90d_count": report.risiko_incidents_90d_count,
        "risiko_incident_burden_level": report.risiko_incident_burden_level,
        "risiko_open_incidents_count": report.risiko_open_incidents_count,
        "risiko_regulatory_priority_note_de": report.risiko_regulatory_priority_note_de,
    }


def enrich_advisor_tenant_report_with_governance_maturity_brief(
    session: Session,
    tenant_id: str,
    report: AdvisorTenantReport,
) -> AdvisorTenantReport:
    """Setzt optional `governance_maturity_advisor_brief` (Feature governance_maturity)."""
    res = maybe_build_advisor_governance_maturity_brief_result(
        session,
        tenant_id,
        incident_drilldown=report.incident_drilldown_snapshot,
    )
    if res is None:
        return report
    return report.model_copy(update={"governance_maturity_advisor_brief": res.brief})


def maybe_enrich_advisor_report_with_llm_summary(
    session: Session,
    tenant_id: str,
    report: AdvisorTenantReport,
) -> AdvisorTenantReport:
    """
    Wenn LLM-Features aktiv sind und der Router erfolgreich antwortet, ergänzt eine
    Executive-Summary-Formulierung; bei Fehler oder deaktiviertem Feature unverändert.
    """
    if not is_feature_enabled(FeatureFlag.llm_enabled, tenant_id, session=session):
        return report
    if not is_feature_enabled(FeatureFlag.llm_report_assistant, tenant_id, session=session):
        return report

    facts = _deterministic_facts_payload(report)
    prompt = (
        "Formuliere eine Executive Summary auf Deutsch in 3–5 kurzen Sätzen, sachlich und "
        "ohne Superlative. Nutze ausschließlich die folgenden JSON-Fakten; erfinde keine "
        "neuen Zahlen, keine neuen regulatorischen Behauptungen und keine Systemnamen, "
        "die nicht in den Fakten stehen.\n\n"
        f"{json.dumps(facts, ensure_ascii=False)}"
    )
    scan = scan_input_for_pii_and_injection(prompt)
    log_input_guardrail_scan(
        context="advisor_report_executive_summary",
        tenant_id=tenant_id,
        scan=scan,
    )
    try:
        router = LLMRouter(session=session)
        resp = router.route_and_call(LLMTaskType.STRUCTURED_OUTPUT, prompt, tenant_id)
    except Exception:
        logger.exception("advisor_report_llm_enrichment_failed tenant=%s", tenant_id)
        return report
    text = (resp.text or "").strip()
    if not text:
        return report
    return report.model_copy(update={"executive_summary_narrative": text})
