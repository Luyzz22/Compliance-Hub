"""Optional audit_events rows for LLM failures (evidence views; no prompt content)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.repositories.audit import AuditRepository

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def log_llm_contract_violation_audit(
    session: Session | None,
    *,
    tenant_id: str,
    action_name: str,
    task_type: str,
    contract_schema: str,
) -> None:
    if session is None:
        return
    try:
        AuditRepository(session).log_event(
            tenant_id=tenant_id,
            actor_type="llm",
            actor_id=None,
            entity_type="llm_contract_violation",
            entity_id=tenant_id,
            action="contract_violation",
            metadata={
                "llm_action_name": action_name,
                "task_type": task_type,
                "contract_schema": contract_schema,
                "error_class": "LLMContractViolation",
            },
        )
    except Exception:
        logger.exception("log_llm_contract_violation_audit_failed tenant_id=%s", tenant_id)


def log_llm_guardrail_block_audit(
    session: Session | None,
    *,
    tenant_id: str,
    action_name: str,
    error_class: str,
    task_type: str | None = None,
) -> None:
    if session is None:
        return
    try:
        AuditRepository(session).log_event(
            tenant_id=tenant_id,
            actor_type="llm",
            actor_id=None,
            entity_type="llm_guardrail_block",
            entity_id=tenant_id,
            action="blocked",
            metadata={
                "llm_action_name": action_name,
                "task_type": task_type,
                "error_class": error_class,
            },
        )
    except Exception:
        logger.exception("log_llm_guardrail_block_audit_failed tenant_id=%s", tenant_id)
