"""Guardrailed prompt builder for RAG-based advisory answers.

Constructs structured German prompts from retrieved documents with:
- Citation requirements (doc_id references)
- Language enforcement (German for DACH market)
- Compliance guardrails (no speculation beyond retrieved sources)
- Confidence-aware phrasing
"""

from __future__ import annotations

from app.services.rag.corpus import RetrievalResponse

_SYSTEM_PROMPT = """\
Du bist ein Compliance-Berater für die ComplianceHub-Plattform.
Beantworte die Frage NUR basierend auf den bereitgestellten Quelldokumenten.

REGELN:
1. Antworte auf Deutsch.
2. Zitiere jede Aussage mit [doc_id] des Quelldokuments.
3. Wenn die Quellen die Frage nicht beantworten, sage das explizit.
4. Spekuliere NICHT über Inhalte, die nicht in den Quellen stehen.
5. Bei Unsicherheit empfehle eine menschliche Prüfung.
"""

_CONFIDENCE_CAVEATS = {
    "high": "",
    "medium": (
        "\n⚠️ HINWEIS: Die Konfidenz der Quellenübereinstimmung ist mittel. "
        "Empfehlung: Antwort durch Fachberater verifizieren lassen.\n"
    ),
    "low": (
        "\n⚠️ WARNUNG: Die Quellenübereinstimmung ist gering. "
        "Eine automatische Beantwortung wird nicht empfohlen. "
        "Bitte leiten Sie die Anfrage an einen Fachberater weiter.\n"
    ),
}


def build_rag_prompt(
    query: str,
    response: RetrievalResponse,
) -> str:
    """Build a complete prompt for the synthesize_answer LLM node."""
    context_blocks = []
    for r in response.results:
        block = (
            f"--- Quelle [{r.doc.doc_id}] ---\n"
            f"Titel: {r.doc.title}\n"
            f"Regulierung: {r.doc.source}"
        )
        if r.doc.section:
            block += f" – {r.doc.section}"
        block += f"\nRelevanz-Score: {r.score:.2f}\n\n{r.doc.content}\n"
        context_blocks.append(block)

    no_sources = "(Keine relevanten Quellen gefunden.)"
    context_text = "\n".join(context_blocks) if context_blocks else no_sources
    caveat = _CONFIDENCE_CAVEATS.get(response.confidence_level, "")

    return (
        f"{_SYSTEM_PROMPT}\n"
        f"{caveat}\n"
        f"=== QUELLDOKUMENTE ===\n{context_text}\n\n"
        f"=== FRAGE ===\n{query}\n\n"
        f"=== ANTWORT ===\n"
    )
