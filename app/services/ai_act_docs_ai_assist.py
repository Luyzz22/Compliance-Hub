"""LLM-Entwürfe für EU-AI-Act-Dokumentationssektionen (ohne Persistenz)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from app.ai_act_doc_models import AIActDoc, AIActDocContentSource, AIActDocSectionKey
from app.ai_system_models import AISystem
from app.classification_models import RiskClassification
from app.llm_models import LLMTaskType
from app.nis2_kritis_models import Nis2KritisKpi
from app.services.llm_json_utils import LLMJsonParseError, extract_json_object
from app.services.llm_router import LLMRouter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _section_instruction(section_key: AIActDocSectionKey) -> str:
    return {
        AIActDocSectionKey.RISK_MANAGEMENT: (
            "Risikomanagementsystem gemäß EU AI Act (High-Risk): Identifikation, Analyse, "
            "Bewertung und Mitigation von Risiken für Gesundheit, Sicherheit und Grundrechte."
        ),
        AIActDocSectionKey.DATA_GOVERNANCE: (
            "Daten-Governance und Datenbestände: Trainings-, Validierungs- und Testdaten, "
            "Datenqualität, Verarbeitungsgrundlagen, DSGVO-Relevanz."
        ),
        AIActDocSectionKey.MONITORING_LOGGING: (
            "Überwachung nach Inverkehrbringen, Logging, Aufzeichnungspflichten "
            "und Nachvollziehbarkeit."
        ),
        AIActDocSectionKey.HUMAN_OVERSIGHT: (
            "Menschliche Aufsicht: Schnittstellen zu menschlicher Kontrolle, Eskalation, "
            "Interventionsmöglichkeiten."
        ),
        AIActDocSectionKey.TECHNICAL_ROBUSTNESS: (
            "Technische Robustheit, Cybersecurity, Genauigkeit und "
            "Widerstandsfähigkeit gegen Fehlbedienung."
        ),
    }[section_key]


def generate_ai_act_doc_draft(
    ai_system: AISystem,
    section_key: AIActDocSectionKey,
    tenant_id: str,
    *,
    session: Session | None,
    classification: RiskClassification | None,
    nis2_kpis: list[Nis2KritisKpi],
    actions_brief: list[dict[str, str]],
    evidence_file_count: int,
) -> AIActDoc:
    kpis_blob = [
        {"kpi_type": k.kpi_type.value, "value_percent": k.value_percent} for k in nis2_kpis
    ]
    cls_blob = None
    if classification is not None:
        cls_blob = {
            "risk_level": classification.risk_level,
            "classification_path": classification.classification_path,
            "annex_iii_category": classification.annex_iii_category,
            "rationale_excerpt": (classification.classification_rationale or "")[:1200],
        }
    facts = {
        "ai_system": {
            "id": ai_system.id,
            "name": ai_system.name,
            "description": ai_system.description[:2000],
            "business_unit": ai_system.business_unit,
            "risk_level": str(ai_system.risk_level),
            "ai_act_category": str(ai_system.ai_act_category),
            "criticality": str(ai_system.criticality),
            "has_incident_runbook": ai_system.has_incident_runbook,
            "has_backup_runbook": ai_system.has_backup_runbook,
            "has_supplier_risk_register": ai_system.has_supplier_risk_register,
        },
        "classification": cls_blob,
        "nis2_kritis_kpis": kpis_blob,
        "open_actions_brief": actions_brief[:12],
        "evidence_attachment_count": evidence_file_count,
    }
    facts_json = json.dumps(facts, ensure_ascii=False, indent=2)
    section_line = _section_instruction(section_key)

    legal_prompt = (
        "Du bist ein Compliance-Autor für die technische Dokumentation von High-Risk-KI-Systemen "
        "nach EU AI Act (Anhang IV / Art. 11). "
        "Nutze ausschließlich die mitgelieferten Fakten – keine erfundenen Projekte, keine "
        "erfundenen Zertifikate oder Behördenkontakte.\n\n"
        f"Sektion: {section_key.value}\n{section_line}\n\n"
        "Fasse in 5–10 Stichpunkten (Deutsch) die wichtigsten inhaltlichen Punkte zusammen, "
        "die in die Dokumentation gehören. Verweise auf Lücken nur, wenn die Fakten es "
        "nahelegen.\n\n"
        f"Fakten (JSON):\n{facts_json}\n"
    )

    router = LLMRouter(session=session)
    legal_out = router.route_and_call(LLMTaskType.LEGAL_REASONING, legal_prompt, tenant_id).text

    structured_prompt = (
        "Erzeuge die eigentliche Dokumentationssektion als strukturiertes Markdown für Auditoren.\n"
        "Antwort NUR als JSON-Objekt mit genau diesen Schlüsseln:\n"
        '  "title": kurzer deutscher Titel (max 120 Zeichen),\n'
        '  "content_markdown": Markdown mit ##-Überschriften, 3–8 Absätze, '
        "sachlich, ohne Fiktion.\n\n"
        f"Ziel-Sektion: {section_key.value}\n"
        f"Stichpunkte aus juristisch-technischer Voranalyse:\n{legal_out}\n\n"
        f"Fakten (JSON, maßgeblich):\n{facts_json}\n"
    )
    resp2 = router.route_and_call(
        LLMTaskType.STRUCTURED_OUTPUT,
        structured_prompt,
        tenant_id,
        response_format="json_object",
    )
    try:
        data = extract_json_object(resp2.text)
    except LLMJsonParseError as exc:
        raise ValueError(f"LLM output not valid JSON: {exc}") from exc

    title = data.get("title")
    body = data.get("content_markdown")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("missing title in LLM JSON")
    if not isinstance(body, str):
        raise ValueError("missing content_markdown in LLM JSON")

    now = datetime.utcnow()
    return AIActDoc(
        id=str(uuid4()),
        tenant_id=tenant_id,
        ai_system_id=ai_system.id,
        section_key=section_key,
        title=title.strip()[:500],
        content_markdown=body.strip(),
        version=0,
        content_source=AIActDocContentSource.ai_generated,
        created_at=now,
        created_by="llm_draft",
        updated_at=now,
        updated_by="llm_draft",
    )
