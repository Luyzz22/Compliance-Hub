"""Feature-Flags (ENV-gesteuert, optional später tenant-spezifisch erweiterbar)."""

from __future__ import annotations

import os
from enum import StrEnum

from fastapi import HTTPException, status
from sqlalchemy.orm import Session


class FeatureFlag(StrEnum):
    advisor_workspace = "advisor_workspace"
    api_keys_ui = "api_keys_ui"
    demo_seeding = "demo_seeding"
    evidence_uploads = "evidence_uploads"
    guided_setup = "guided_setup"
    pilot_runbook = "pilot_runbook"
    llm_enabled = "llm_enabled"
    llm_legal_reasoning = "llm_legal_reasoning"
    llm_report_assistant = "llm_report_assistant"
    llm_classification_tagging = "llm_classification_tagging"
    llm_chat_assistant = "llm_chat_assistant"
    llm_kpi_suggestions = "llm_kpi_suggestions"
    llm_explain = "llm_explain"
    llm_action_drafts = "llm_action_drafts"
    ai_act_docs = "ai_act_docs"
    what_if_simulator = "what_if_simulator"
    ai_governance_playbook = "ai_governance_playbook"
    cross_regulation_dashboard = "cross_regulation_dashboard"
    cross_regulation_llm_assist = "cross_regulation_llm_assist"
    ai_compliance_board_report = "ai_compliance_board_report"
    ai_kpi_kri = "ai_kpi_kri"
    ai_governance_setup_wizard = "ai_governance_setup_wizard"
    advisor_client_snapshot = "advisor_client_snapshot"
    readiness_score = "readiness_score"


_FLAG_ENV_KEYS: dict[FeatureFlag, str] = {
    FeatureFlag.advisor_workspace: "COMPLIANCEHUB_FEATURE_ADVISOR_WORKSPACE",
    FeatureFlag.api_keys_ui: "COMPLIANCEHUB_FEATURE_API_KEYS_UI",
    FeatureFlag.demo_seeding: "COMPLIANCEHUB_FEATURE_DEMO_SEEDING",
    FeatureFlag.evidence_uploads: "COMPLIANCEHUB_FEATURE_EVIDENCE_UPLOADS",
    FeatureFlag.guided_setup: "COMPLIANCEHUB_FEATURE_GUIDED_SETUP",
    FeatureFlag.pilot_runbook: "COMPLIANCEHUB_FEATURE_PILOT_RUNBOOK",
    FeatureFlag.llm_enabled: "COMPLIANCEHUB_FEATURE_LLM_ENABLED",
    FeatureFlag.llm_legal_reasoning: "COMPLIANCEHUB_FEATURE_LLM_LEGAL_REASONING",
    FeatureFlag.llm_report_assistant: "COMPLIANCEHUB_FEATURE_LLM_REPORT_ASSISTANT",
    FeatureFlag.llm_classification_tagging: "COMPLIANCEHUB_FEATURE_LLM_CLASSIFICATION_TAGGING",
    FeatureFlag.llm_chat_assistant: "COMPLIANCEHUB_FEATURE_LLM_CHAT_ASSISTANT",
    FeatureFlag.llm_kpi_suggestions: "COMPLIANCEHUB_FEATURE_LLM_KPI_SUGGESTIONS",
    FeatureFlag.llm_explain: "COMPLIANCEHUB_FEATURE_LLM_EXPLAIN",
    FeatureFlag.llm_action_drafts: "COMPLIANCEHUB_FEATURE_LLM_ACTION_DRAFTS",
    FeatureFlag.ai_act_docs: "COMPLIANCEHUB_FEATURE_AI_ACT_DOCS",
    FeatureFlag.what_if_simulator: "COMPLIANCEHUB_FEATURE_WHAT_IF_SIMULATOR",
    FeatureFlag.ai_governance_playbook: "COMPLIANCEHUB_FEATURE_AI_GOVERNANCE_PLAYBOOK",
    FeatureFlag.cross_regulation_dashboard: "COMPLIANCEHUB_FEATURE_CROSS_REGULATION_DASHBOARD",
    FeatureFlag.cross_regulation_llm_assist: "COMPLIANCEHUB_FEATURE_CROSS_REGULATION_LLM_ASSIST",
    FeatureFlag.ai_compliance_board_report: "COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT",
    FeatureFlag.ai_kpi_kri: "COMPLIANCEHUB_FEATURE_AI_KPI_KRI",
    FeatureFlag.ai_governance_setup_wizard: "COMPLIANCEHUB_FEATURE_AI_GOVERNANCE_SETUP_WIZARD",
    FeatureFlag.advisor_client_snapshot: "COMPLIANCEHUB_FEATURE_ADVISOR_CLIENT_SNAPSHOT",
    FeatureFlag.readiness_score: "COMPLIANCEHUB_FEATURE_READINESS_SCORE",
}

# LLM master switch defaults off until keys and policies are configured.
_FLAG_DEFAULTS: dict[FeatureFlag, bool] = {
    FeatureFlag.llm_enabled: False,
    FeatureFlag.llm_kpi_suggestions: False,
    FeatureFlag.llm_explain: False,
    FeatureFlag.llm_action_drafts: False,
}


def _parse_env_bool(key: str, *, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def is_feature_enabled(
    flag: FeatureFlag,
    tenant_id: str | None = None,
    *,
    session: Session | None = None,
) -> bool:
    """
    Prüft, ob ein Feature aktiv ist.

    Mit tenant_id und session: zuerst Override in tenant_feature_flag_overrides, sonst ENV.
    """
    if tenant_id is not None and session is not None:
        from app.repositories.tenant_feature_overrides import TenantFeatureOverrideRepository

        repo = TenantFeatureOverrideRepository(session)
        override = repo.get_override(tenant_id, flag.value)
        if override is not None:
            return override

    env_key = _FLAG_ENV_KEYS[flag]
    default = _FLAG_DEFAULTS.get(flag, True)
    return _parse_env_bool(env_key, default=default)


def create_feature_guard(flag: FeatureFlag):
    """FastAPI-Depends: 403, wenn Feature ausgeschaltet."""

    def _guard() -> None:
        if not is_feature_enabled(flag):
            env_key = _FLAG_ENV_KEYS[flag]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Feature '{flag.value}' is disabled. Enable via {env_key}=true "
                    f"(omit or set true for default-on in dev)."
                ),
            )

    return _guard


def require_tenant_llm_features(
    tenant_id: str,
    session: Session,
    *flags: FeatureFlag,
) -> None:
    """403 wenn LLM-Master oder ein angefordertes Teil-Feature für den Mandanten aus ist."""
    if not is_feature_enabled(FeatureFlag.llm_enabled, tenant_id, session=session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="LLM features are disabled for this tenant (COMPLIANCEHUB_FEATURE_LLM_ENABLED).",
        )
    for flag in flags:
        if not is_feature_enabled(flag, tenant_id, session=session):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{flag.value}' is disabled for this tenant.",
            )
