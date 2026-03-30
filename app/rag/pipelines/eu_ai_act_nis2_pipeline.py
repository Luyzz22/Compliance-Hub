"""
EU AI Act / NIS2 / ISO 42001 advisor RAG — explicit Haystack 2 graph.

Graph (BM25 pilot):
  ``query`` → Retriever → PromptBuilder → Guardrailed Generator → structured JSON

All nodes are dedicated component classes (no hidden lambdas). The generator uses
``safe_llm_call_sync`` + ``LlmCallContext`` so guardrails and task routing match the rest
of ComplianceHub.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from haystack import Pipeline, component
from haystack.components.retrievers import InMemoryBM25Retriever
from haystack.dataclasses import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore

from app.llm.client_wrapped import safe_llm_call_sync
from app.llm.context import LlmCallContext
from app.llm_models import LLMTaskType
from app.rag.haystack_config import rag_retriever_top_k
from app.rag.models import EuRegRagLlmOutput

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_SYSTEM_DE = (
    "Du bist ein Compliance-Assistent für Berater im DACH-Raum. Antworte auf Deutsch, sachlich, "
    "ohne Rechtsberatung. Nutze ausschließlich die unten nummerierten Kurzfragmente; keine "
    "externen Fakten. Wenn der Kurpus nicht reicht, sage das klar.\n\n"
    "Gib die Antwort als ein JSON-Objekt mit genau diesen Schlüsseln:\n"
    '- "answer_de": string (Markdown erlaubt, max. knapp)\n'
    '- "citations": Liste von Objekten mit "doc_id", "source", "section" '
    "(höchstens 5 Einträge; doc_id exakt wie im Katalog).\n\n"
)


@component
class EuAiActNis2PromptBuilder:
    """Builds the LLM prompt and a machine-readable source catalog from retrieved docs."""

    @component.output_types(prompt=str, retrieved_documents=list)
    def run(self, query: str, documents: list[Document]) -> dict[str, object]:
        catalog_lines: list[str] = []
        for i, doc in enumerate(documents, start=1):
            did = str(doc.id or f"doc-{i}")
            meta = doc.meta or {}
            source = str(meta.get("source", ""))
            section = str(meta.get("section", ""))
            body = (doc.content or "").strip()
            catalog_lines.append(
                f"[{i}] doc_id={did!r} source={source!r} section={section!r}\n{body}\n",
            )
        catalog = "\n".join(catalog_lines) if catalog_lines else "(Keine Treffer im Kurpus.)"
        prompt = (
            f"{_SYSTEM_DE}--- Kurpus ---\n{catalog}\n--- Frage ---\n{query.strip()}\n--- JSON ---\n"
        )
        return {"prompt": prompt, "retrieved_documents": documents}


@component
class GuardrailedEuRegRagGenerator:
    """LLM step: guardrailed structured JSON via existing ComplianceHub client."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    @component.output_types(structured=dict)
    def run(self, prompt: str, tenant_id: str, user_role: str) -> dict[str, object]:
        ctx = LlmCallContext(
            tenant_id=tenant_id.strip(),
            user_role=(user_role or "").strip(),
            action_name="advisor_rag_eu_ai_act_nis2_query",
        )
        try:
            parsed = safe_llm_call_sync(
                prompt,
                EuRegRagLlmOutput,
                context=ctx,
                session=self._session,
                task_type=LLMTaskType.ADVISOR_REGULATORY_RAG,
            )
            payload = parsed.model_dump(mode="json")
        except Exception as exc:
            logger.exception(
                "eu_reg_rag_generator_failed tenant=%s err=%s",
                tenant_id,
                type(exc).__name__,
            )
            payload = EuRegRagLlmOutput(
                answer_de=(
                    "Die KI-Antwort konnte nicht verlässlich erzeugt werden. "
                    "Bitte LLM-Konfiguration prüfen."
                ),
                citations=[],
            ).model_dump(mode="json")
        return {"structured": payload}


def build_eu_ai_act_nis2_pipeline(
    document_store: InMemoryDocumentStore,
    *,
    session: Session | None = None,
    top_k: int | None = None,
) -> Pipeline:
    k = top_k if top_k is not None else rag_retriever_top_k()
    retriever = InMemoryBM25Retriever(document_store=document_store, top_k=k)
    prompt_builder = EuAiActNis2PromptBuilder()
    generator = GuardrailedEuRegRagGenerator(session=session)

    pipeline = Pipeline()
    pipeline.add_component("retriever", retriever)
    pipeline.add_component("prompt_builder", prompt_builder)
    pipeline.add_component("generator", generator)
    pipeline.connect("retriever.documents", "prompt_builder.documents")
    pipeline.connect("prompt_builder.prompt", "generator.prompt")
    return pipeline


def run_eu_ai_act_nis2_pipeline(
    *,
    question_de: str,
    tenant_id: str,
    user_role: str,
    document_store: InMemoryDocumentStore,
    session: Session | None = None,
    top_k: int | None = None,
) -> tuple[dict, list[Document]]:
    """
    Execute the full graph. Returns (generator structured dict, retrieved documents).
    """
    pipe = build_eu_ai_act_nis2_pipeline(
        document_store,
        session=session,
        top_k=top_k,
    )
    q = question_de.strip()
    out = pipe.run(
        {
            "retriever": {"query": q},
            "prompt_builder": {"query": q},
            "generator": {"tenant_id": tenant_id, "user_role": user_role},
        },
    )
    structured = out["generator"]["structured"]
    documents = out["prompt_builder"]["retrieved_documents"]
    if isinstance(structured, str):
        structured = json.loads(structured)
    return structured, documents
