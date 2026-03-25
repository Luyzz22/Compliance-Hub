"""Resolve TenantLLMPolicy: defaults, ENV map, optional DB override."""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any

from app.llm_models import (
    DataResidencyPolicy,
    LLMProvider,
    LLMTaskType,
    PublicApiPolicy,
    TenantLLMPolicy,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_ENV_TENANT_POLICIES = "COMPLIANCEHUB_LLM_TENANT_POLICIES_JSON"


def _default_provider_by_task() -> dict[LLMTaskType, LLMProvider]:
    return {
        LLMTaskType.LEGAL_REASONING: LLMProvider.CLAUDE,
        LLMTaskType.STRUCTURED_OUTPUT: LLMProvider.OPENAI,
        LLMTaskType.CLASSIFICATION_TAGGING: LLMProvider.GEMINI,
        LLMTaskType.CHAT_ASSISTANT: LLMProvider.OPENAI,
        LLMTaskType.EMBEDDING_RETRIEVAL: LLMProvider.LLAMA,
        LLMTaskType.ON_PREM_SENSITIVE: LLMProvider.LLAMA,
    }


def default_tenant_llm_policy(tenant_id: str) -> TenantLLMPolicy:
    return TenantLLMPolicy(
        tenant_id=tenant_id,
        allowed_providers=list(LLMProvider),
        default_provider_by_task=_default_provider_by_task(),
        require_on_prem_for_sensitive=False,
        data_residency=DataResidencyPolicy.US_CLOUD_ALLOWED,
        public_api_policy=PublicApiPolicy.PUBLIC_API_ALLOWED,
    )


def _deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def _load_env_tenant_fragment(tenant_id: str) -> dict[str, Any] | None:
    raw = os.getenv(_ENV_TENANT_POLICIES)
    if not raw or not str(raw).strip():
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("invalid_json_for_%s", _ENV_TENANT_POLICIES)
        return None
    if not isinstance(data, dict):
        return None
    frag = data.get(tenant_id)
    return frag if isinstance(frag, dict) else None


def _policy_from_merged_dict(tenant_id: str, merged: dict[str, Any]) -> TenantLLMPolicy:
    payload = {**merged, "tenant_id": tenant_id}
    return TenantLLMPolicy.model_validate(payload)


def get_tenant_llm_policy(tenant_id: str, session: Session | None = None) -> TenantLLMPolicy:
    """
    Standard-Policy für alle Provider; Merge-Reihenfolge:
    1) default_tenant_llm_policy
    2) COMPLIANCEHUB_LLM_TENANT_POLICIES_JSON[tenant_id]
    3) tenant_llm_policy_overrides.policy_json (wenn session und Zeile vorhanden)
    """
    base = default_tenant_llm_policy(tenant_id).model_dump(mode="json")
    merged = dict(base)

    env_frag = _load_env_tenant_fragment(tenant_id)
    if env_frag:
        merged = _deep_merge_dict(merged, env_frag)

    if session is not None:
        from app.repositories.tenant_llm_policy_override import TenantLLMPolicyOverrideRepository

        repo = TenantLLMPolicyOverrideRepository(session)
        db_frag = repo.get_partial_dict(tenant_id)
        if db_frag:
            merged = _deep_merge_dict(merged, db_frag)

    return _policy_from_merged_dict(tenant_id, merged)
