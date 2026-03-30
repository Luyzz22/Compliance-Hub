"""Application service: advisor EU regulatory RAG (Haystack + guardrails)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from haystack.document_stores.in_memory import InMemoryDocumentStore

from app.rag.models import EuAiActNis2RagCitation, EuAiActNis2RagResponse, EuRegRagLlmOutput
from app.rag.pipelines.eu_ai_act_nis2_pipeline import run_eu_ai_act_nis2_pipeline
from app.rag.store import get_eu_reg_document_store

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def run_advisor_eu_reg_rag(
    *,
    question_de: str,
    tenant_id: str,
    user_role: str,
    advisor_id: str,
    session: Session | None,
    document_store: InMemoryDocumentStore | None = None,
) -> EuAiActNis2RagResponse:
    store = document_store or get_eu_reg_document_store()
    structured, _docs = run_eu_ai_act_nis2_pipeline(
        question_de=question_de,
        tenant_id=tenant_id,
        user_role=user_role,
        document_store=store,
        session=session,
    )
    parsed = EuRegRagLlmOutput.model_validate(structured)
    citations = [
        EuAiActNis2RagCitation(doc_id=c.doc_id, source=c.source, section=c.section)
        for c in (parsed.citations or [])[:3]
    ]
    logger.info(
        "advisor_eu_reg_rag_done advisor_id=%s tenant_id=%s citation_count=%s",
        advisor_id,
        tenant_id,
        len(citations),
    )
    return EuAiActNis2RagResponse(answer_de=parsed.answer_de, citations=citations)
