"""Task-aware LLM routing with tenant policy, residency rules, and metadata logging."""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from app.llm_models import (
    CostSensitivity,
    DataResidencyPolicy,
    LatencySensitivity,
    LLMCallMetadataRecord,
    LLMProvider,
    LLMResponse,
    LLMTaskType,
    PublicApiPolicy,
    TenantLLMPolicy,
)
from app.services import llm_client
from app.services.llm_task_flags import is_llm_task_feature_enabled
from app.services.tenant_llm_policy import get_tenant_llm_policy

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _parse_env_bool(key: str) -> bool:
    raw = os.getenv(key)
    if raw is None or not str(raw).strip():
        return False
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _us_cloud_eu_exception_allowed() -> bool:
    """Operator attestation: vendor API used under EU data residency / DPA."""
    return _parse_env_bool("COMPLIANCEHUB_LLM_US_CLOUD_OK")


def _claude_eu_attested() -> bool:
    """Operator attestation: Claude traffic stays in approved EU/EEA processing."""
    return _parse_env_bool("COMPLIANCEHUB_LLM_ASSUME_CLAUDE_EU")


def _static_fallback_chain(task_type: LLMTaskType) -> list[LLMProvider]:
    if task_type == LLMTaskType.LEGAL_REASONING:
        return [LLMProvider.CLAUDE, LLMProvider.OPENAI, LLMProvider.GEMINI, LLMProvider.LLAMA]
    if task_type == LLMTaskType.STRUCTURED_OUTPUT:
        return [LLMProvider.OPENAI, LLMProvider.CLAUDE, LLMProvider.GEMINI, LLMProvider.LLAMA]
    if task_type == LLMTaskType.CLASSIFICATION_TAGGING:
        return [LLMProvider.GEMINI, LLMProvider.OPENAI, LLMProvider.CLAUDE, LLMProvider.LLAMA]
    if task_type == LLMTaskType.CHAT_ASSISTANT:
        return [LLMProvider.OPENAI, LLMProvider.CLAUDE, LLMProvider.GEMINI, LLMProvider.LLAMA]
    if task_type == LLMTaskType.EMBEDDING_RETRIEVAL:
        return [LLMProvider.LLAMA, LLMProvider.OPENAI]
    if task_type == LLMTaskType.ON_PREM_SENSITIVE:
        return [LLMProvider.LLAMA]
    return list(LLMProvider)


def _prefer_low_cost_gemini(
    task_type: LLMTaskType,
    policy: TenantLLMPolicy,
) -> bool:
    if policy.cost_sensitivity != CostSensitivity.HIGH:
        return False
    return task_type in (
        LLMTaskType.CLASSIFICATION_TAGGING,
        LLMTaskType.CHAT_ASSISTANT,
    )


def _prefer_low_latency_gemini(
    task_type: LLMTaskType,
    policy: TenantLLMPolicy,
) -> bool:
    if policy.latency_sensitivity != LatencySensitivity.HIGH:
        return False
    return task_type in (
        LLMTaskType.CLASSIFICATION_TAGGING,
        LLMTaskType.CHAT_ASSISTANT,
    )


def _reorder_gemini_first(chain: list[LLMProvider]) -> list[LLMProvider]:
    if LLMProvider.GEMINI not in chain:
        return chain
    rest = [p for p in chain if p != LLMProvider.GEMINI]
    return [LLMProvider.GEMINI] + rest


def preference_chain(task_type: LLMTaskType, policy: TenantLLMPolicy) -> list[LLMProvider]:
    base = list(_static_fallback_chain(task_type))
    explicit = policy.default_provider_by_task.get(task_type)
    if explicit is not None:
        rest = [p for p in base if p != explicit]
        chain = [explicit] + rest
    else:
        chain = base
    if _prefer_low_cost_gemini(task_type, policy) or _prefer_low_latency_gemini(task_type, policy):
        chain = _reorder_gemini_first(chain)
    return chain


def _allowed_by_residency(provider: LLMProvider, policy: TenantLLMPolicy) -> bool:
    if policy.data_residency == DataResidencyPolicy.US_CLOUD_ALLOWED:
        return True
    if provider == LLMProvider.LLAMA:
        return True
    if provider == LLMProvider.CLAUDE and _claude_eu_attested():
        return True
    if provider in (LLMProvider.OPENAI, LLMProvider.GEMINI) and _us_cloud_eu_exception_allowed():
        return True
    return False


def _allowed_by_public_api(provider: LLMProvider, policy: TenantLLMPolicy) -> bool:
    if policy.public_api_policy == PublicApiPolicy.PUBLIC_API_ALLOWED:
        return True
    return provider == LLMProvider.LLAMA


def filter_candidates(policy: TenantLLMPolicy, ordered: list[LLMProvider]) -> list[LLMProvider]:
    allowed_set = set(policy.allowed_providers)
    out: list[LLMProvider] = []
    seen: set[LLMProvider] = set()
    for p in ordered:
        if p in seen:
            continue
        if p not in allowed_set:
            continue
        if not _allowed_by_residency(p, policy):
            continue
        if not _allowed_by_public_api(p, policy):
            continue
        if not llm_client.is_provider_configured(p):
            continue
        out.append(p)
        seen.add(p)
    return out


class LLMRouter:
    def __init__(
        self,
        session: Session | None = None,
        *,
        call_model_fn: Callable[..., LLMResponse] | None = None,
        call_embedding_fn: Callable[..., LLMResponse] | None = None,
    ) -> None:
        self._session = session
        self._call_model = call_model_fn or llm_client.call_model
        self._call_embedding = call_embedding_fn or llm_client.call_embedding

    def route_and_call(
        self,
        task_type: LLMTaskType,
        prompt: str,
        tenant_id: str,
        **kwargs: Any,
    ) -> LLMResponse:
        if not is_llm_task_feature_enabled(task_type, tenant_id, session=self._session):
            raise PermissionError("LLM task is disabled by feature flags for this tenant")

        policy = get_tenant_llm_policy(tenant_id, self._session)
        ordered = preference_chain(task_type, policy)
        if task_type == LLMTaskType.ON_PREM_SENSITIVE:
            if not llm_client.is_provider_configured(LLMProvider.LLAMA):
                raise llm_client.LLMConfigurationError(
                    "ON_PREM_SENSITIVE requires LLAMA_BASE_URL and a reachable on-prem model",
                )
            ordered = [LLMProvider.LLAMA]
        elif policy.require_on_prem_for_sensitive and task_type == LLMTaskType.LEGAL_REASONING:
            ordered = [LLMProvider.LLAMA] + [p for p in ordered if p != LLMProvider.LLAMA]

        candidates = filter_candidates(policy, ordered)
        if not candidates:
            raise llm_client.LLMConfigurationError(
                "No LLM provider available for this tenant, task type, and policy "
                f"(task={task_type.value})",
            )

        last_err: Exception | None = None
        t0 = time.perf_counter()
        for provider in candidates:
            model_id = (
                llm_client.embedding_model_id(provider)
                if task_type == LLMTaskType.EMBEDDING_RETRIEVAL
                else llm_client.chat_model_id(provider)
            )
            try:
                if task_type == LLMTaskType.EMBEDDING_RETRIEVAL:
                    resp = self._call_embedding(provider, model_id, prompt)
                else:
                    resp = self._call_model(provider, model_id, prompt, **kwargs)
                latency_ms = int((time.perf_counter() - t0) * 1000)
                self._log_metadata(
                    tenant_id=tenant_id,
                    task_type=task_type,
                    provider=resp.provider,
                    model_id=resp.model_id,
                    prompt_length=len(prompt),
                    response_length=len(resp.text),
                    latency_ms=latency_ms,
                    in_tok=resp.input_tokens_est,
                    out_tok=resp.output_tokens_est,
                )
                return resp
            except Exception as exc:
                last_err = exc
                logger.info(
                    "llm_provider_fallback tenant=%s task=%s failed_provider=%s err=%s",
                    tenant_id,
                    task_type.value,
                    provider.value,
                    type(exc).__name__,
                )
                continue

        if last_err is not None:
            raise last_err
        raise llm_client.LLMConfigurationError(
            f"No LLM provider attempt completed for task {task_type.value}",
        )

    def _log_metadata(
        self,
        *,
        tenant_id: str,
        task_type: LLMTaskType,
        provider: LLMProvider,
        model_id: str,
        prompt_length: int,
        response_length: int,
        latency_ms: int,
        in_tok: int,
        out_tok: int,
    ) -> None:
        if self._session is None:
            return
        try:
            from app.repositories.llm_call_metadata import LLMCallMetadataRepository

            repo = LLMCallMetadataRepository(self._session)
            repo.insert(
                LLMCallMetadataRecord(
                    tenant_id=tenant_id,
                    task_type=task_type,
                    provider=provider,
                    model_id=model_id,
                    prompt_length=prompt_length,
                    response_length=response_length,
                    latency_ms=latency_ms,
                    estimated_input_tokens=in_tok,
                    estimated_output_tokens=out_tok,
                ),
            )
        except Exception:
            logger.exception("llm_metadata_log_failed tenant=%s", tenant_id)
