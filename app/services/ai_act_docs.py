"""AI-Act-Dokumentationsbausteine: Defaults, Liste, Upsert."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.ai_act_doc_models import (
    AIActDoc,
    AIActDocListItem,
    AIActDocListResponse,
    AIActDocSectionKey,
    AIActDocUpsertRequest,
)
from app.repositories.ai_act_docs import AIActDocRepository

if TYPE_CHECKING:
    pass

_DEFAULT_TITLES: dict[AIActDocSectionKey, str] = {
    AIActDocSectionKey.RISK_MANAGEMENT: "Risikomanagementsystem",
    AIActDocSectionKey.DATA_GOVERNANCE: "Daten-Governance und Datenbestände",
    AIActDocSectionKey.MONITORING_LOGGING: "Überwachung, Logging und Aufzeichnung",
    AIActDocSectionKey.HUMAN_OVERSIGHT: "Menschliche Aufsicht",
    AIActDocSectionKey.TECHNICAL_ROBUSTNESS: "Technische Robustheit und Sicherheit",
}


def default_section_title(section_key: AIActDocSectionKey) -> str:
    return _DEFAULT_TITLES.get(section_key, section_key.value)


def build_ai_act_doc_list_response(
    ai_system_id: str,
    repo: AIActDocRepository,
    tenant_id: str,
) -> AIActDocListResponse:
    existing = {d.section_key: d for d in repo.list_for_system(tenant_id, ai_system_id)}
    items: list[AIActDocListItem] = []
    for key in AIActDocSectionKey:
        doc = existing.get(key)
        if doc is None or not (doc.content_markdown or "").strip():
            status = "empty"
        else:
            status = "saved"
        items.append(
            AIActDocListItem(
                section_key=key,
                default_title=default_section_title(key),
                doc=doc,
                status=status,
            ),
        )
    return AIActDocListResponse(ai_system_id=ai_system_id, items=items)


def upsert_ai_act_doc(
    repo: AIActDocRepository,
    tenant_id: str,
    ai_system_id: str,
    section_key: AIActDocSectionKey,
    body: AIActDocUpsertRequest,
    actor: str,
) -> AIActDoc:
    return repo.upsert(
        tenant_id=tenant_id,
        ai_system_id=ai_system_id,
        section_key=section_key,
        title=body.title.strip(),
        content_markdown=body.content_markdown,
        actor=actor,
        content_source=body.content_source,
    )
