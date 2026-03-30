"""German compliance prompt construction for EU regulatory RAG (explicit, auditable)."""

from __future__ import annotations

from haystack.dataclasses import Document

from app.rag.retrieval import is_tenant_guidance_document

_SYSTEM_DE = (
    "Du bist ein Compliance-Assistent für Berater im DACH-Raum. Antworte auf Deutsch, sachlich, "
    "ohne Rechtsberatung. Nutze ausschließlich die unten nummerierten Kurzfragmente; keine "
    "externen Fakten. Wenn der Kurpus nicht reicht, sage das klar.\n"
    "Fragmente mit „Mandanten-Leitfaden“ sind interne Mandanten-Hinweise; "
    "„EU/NIS2/ISO-Korpus“ bezieht sich auf den globalen Pilot-Kurpus.\n\n"
    "Gib die Antwort als ein JSON-Objekt mit genau diesen Schlüsseln:\n"
    '- "answer_de": string (Markdown erlaubt, max. knapp)\n'
    '- "citations": Liste von Objekten mit "doc_id", "source", "section" '
    "(höchstens 5 Einträge; doc_id exakt wie im Katalog).\n\n"
)


def build_eu_reg_rag_prompt(query: str, documents: list[Document]) -> str:
    catalog_lines: list[str] = []
    for i, doc in enumerate(documents, start=1):
        did = str(doc.id or f"doc-{i}")
        meta = doc.meta or {}
        source = str(meta.get("source", ""))
        section = str(meta.get("section", ""))
        body = (doc.content or "").strip()
        kind = "Mandanten-Leitfaden" if is_tenant_guidance_document(doc) else "EU/NIS2/ISO-Korpus"
        catalog_lines.append(
            f"[{i}] doc_id={did!r} kind={kind!r} source={source!r} section={section!r}\n{body}\n",
        )
    catalog = "\n".join(catalog_lines) if catalog_lines else "(Keine Treffer im Kurpus.)"
    return f"{_SYSTEM_DE}--- Kurpus ---\n{catalog}\n--- Frage ---\n{query.strip()}\n--- JSON ---\n"
