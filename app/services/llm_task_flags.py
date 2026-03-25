"""Map LLMTaskType to FeatureFlag entries (global + per-task toggles)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.feature_flags import FeatureFlag, is_feature_enabled
from app.llm_models import LLMTaskType

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def is_llm_task_feature_enabled(
    task_type: LLMTaskType,
    tenant_id: str,
    *,
    session: Session | None = None,
) -> bool:
    if not is_feature_enabled(FeatureFlag.llm_enabled, tenant_id, session=session):
        return False
    task_flag = _TASK_FLAG.get(task_type)
    if task_flag is None:
        return True
    return is_feature_enabled(task_flag, tenant_id, session=session)


_TASK_FLAG: dict[LLMTaskType, FeatureFlag] = {
    LLMTaskType.LEGAL_REASONING: FeatureFlag.llm_legal_reasoning,
    LLMTaskType.STRUCTURED_OUTPUT: FeatureFlag.llm_report_assistant,
    LLMTaskType.CLASSIFICATION_TAGGING: FeatureFlag.llm_classification_tagging,
    LLMTaskType.CHAT_ASSISTANT: FeatureFlag.llm_chat_assistant,
    LLMTaskType.KPI_SUGGESTION_ASSIST: FeatureFlag.llm_kpi_suggestions,
    LLMTaskType.EXPLAIN_KPI_ALERT: FeatureFlag.llm_explain,
    LLMTaskType.ACTION_DRAFT_GENERATION: FeatureFlag.llm_action_drafts,
}
