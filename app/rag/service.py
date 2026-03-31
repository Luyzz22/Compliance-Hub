"""Application service: advisor EU regulatory RAG (Haystack + guardrails)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal, cast

from haystack.dataclasses import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore

from app.rag.models import (
    EuAiActNis2RagCitation,
    EuAiActNis2RagResponse,
    EuRegRagLlmOutput,
    RagRetrievalHitAuditRow,
)
from app.rag.pipelines.eu_ai_act_nis2_pipeline import run_eu_ai_act_nis2_pipeline
from app.rag.retrieval import is_tenant_guidance_document
from app.rag.store import get_eu_reg_document_store
from app.telemetry.tracing import start_span

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _build_api_citations(
    parsed: EuRegRagLlmOutput,
    documents_for_prompt: list[Document],
    *,
    max_citations: int = 3,
) -> list[EuAiActNis2RagCitation]:
    by_id = {str(d.id): d for d in documents_for_prompt if d.id}
    out: list[EuAiActNis2RagCitation] = []
    for c in (parsed.citations or [])[:max_citations]:
        doc = by_id.get(c.doc_id)
        is_tenant = is_tenant_guidance_document(doc) if doc is not None else False
        title = str((doc.meta or {}).get("section", c.section)) if doc is not None else c.section
        out.append(
            EuAiActNis2RagCitation(
                doc_id=c.doc_id,
                source_id=c.doc_id,
                title=title,
                section=c.section,
                source=c.source,
                is_tenant_specific=is_tenant,
            ),
        )
    return out


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
    with start_span(
        "rag.query_received",
        tenant_id=tenant_id,
        user_role=user_role,
        advisor_id=advisor_id,
    ):
        pr = run_eu_ai_act_nis2_pipeline(
            question_de=question_de,
            tenant_id=tenant_id,
            user_role=user_role,
            document_store=store,
            session=session,
            advisor_id=advisor_id,
        )
    parsed = EuRegRagLlmOutput.model_validate(pr.structured)
    citations = _build_api_citations(parsed, pr.documents_for_prompt)
    logger.info(
        "advisor_eu_reg_rag_done advisor_id=%s tenant_id=%s citation_count=%s confidence=%s llm=%s",
        advisor_id,
        tenant_id,
        len(citations),
        pr.confidence_level,
        pr.used_llm,
    )
    conf = cast(Literal["high", "medium", "low"], pr.confidence_level)
    hit_audit = (
        [RagRetrievalHitAuditRow.model_validate(row) for row in pr.retrieval_hit_audit]
        if pr.retrieval_hit_audit
        else None
    )
    rm: Literal["bm25", "hybrid"] | None = None
    if pr.retrieval_mode in ("bm25", "hybrid"):
        rm = cast(Literal["bm25", "hybrid"], pr.retrieval_mode)
    return EuAiActNis2RagResponse(
        answer_de=parsed.answer_de,
        citations=citations,
        confidence_level=conf,
        notes_de=pr.notes_de,
        retrieval_mode=rm,
        retrieval_hit_audit=hit_audit,
    )
