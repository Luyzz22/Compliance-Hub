"""LLM-gestützte NIS2-/KRITIS-KPI-Vorschläge aus Freitext (ohne DB-Persistenz)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from app.ai_system_models import AISystem
from app.llm_models import LLMTaskType
from app.nis2_kritis_models import (
    Nis2KritisKpiSuggestion,
    Nis2KritisKpiSuggestionRequest,
    Nis2KritisKpiSuggestionResponse,
    Nis2KritisKpiType,
)
from app.services.llm_json_utils import LLMJsonParseError, extract_json_object
from app.services.llm_router import LLMRouter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _kpi_scale_help() -> str:
    return (
        "INCIDENT_RESPONSE_MATURITY: 0–100% = Reife Incident-/Backup-Runbooks und operativer "
        "Reaktionsfähigkeit (NIS2/KRITIS).\n"
        "SUPPLIER_RISK_COVERAGE: 0–100% = Abdeckung Lieferketten-/Supplier-Risiko (Register, "
        "Bewertungen).\n"
        "OT_IT_SEGREGATION: 0–100% = Trennung OT/IT und angemessene Segmentierung für "
        "KRITIS-relevante Systeme."
    )


def generate_nis2_kpi_suggestions(
    ai_system: AISystem,
    request: Nis2KritisKpiSuggestionRequest,
    tenant_id: str,
    *,
    session: Session | None,
    existing_kpis_summary: list[dict] | None = None,
) -> Nis2KritisKpiSuggestionResponse:
    if request.ai_system_id != ai_system.id:
        raise ValueError("ai_system_id mismatch")

    ctx_kpis = json.dumps(existing_kpis_summary or [], ensure_ascii=False)
    system_blob = json.dumps(
        {
            "id": ai_system.id,
            "name": ai_system.name,
            "description": ai_system.description[:2000],
            "business_unit": ai_system.business_unit,
            "risk_level": str(ai_system.risk_level),
            "ai_act_category": str(ai_system.ai_act_category),
            "criticality": str(ai_system.criticality),
            "data_sensitivity": str(ai_system.data_sensitivity),
            "has_incident_runbook": ai_system.has_incident_runbook,
            "has_backup_runbook": ai_system.has_backup_runbook,
            "has_supplier_risk_register": ai_system.has_supplier_risk_register,
        },
        ensure_ascii=False,
    )

    prompt = (
        "Du bist ein Governance-Assistent für NIS2/KRITIS-KPIs. "
        "Antworte NUR mit einem JSON-Objekt (kein Markdown), exakt dieses Schema:\n"
        '{"suggestions": [\n'
        '  {"kpi_type": "<INCIDENT_RESPONSE_MATURITY|SUPPLIER_RISK_COVERAGE|OT_IT_SEGREGATION>",\n'
        '   "suggested_value_percent": <int 0-100>,\n'
        '   "confidence": <float 0-1>,\n'
        '   "rationale": "<kurz, deutsch>"}\n'
        "]}\n"
        "Liefere genau einen Eintrag pro kpi_type (3 Einträge). "
        "Keine Speicherung durch das Modell – nur konservative Schätzungen aus den Fakten.\n\n"
        f"KPI-Skalen:\n{_kpi_scale_help()}\n\n"
        f"KI-System (JSON):\n{system_blob}\n\n"
        f"Bestehende KPI-Zeilen (falls leer: unbekannt):\n{ctx_kpis}\n\n"
        f"Nutzer-Freitext:\n{request.free_text.strip()}\n"
    )

    router = LLMRouter(session=session)
    resp = router.route_and_call(LLMTaskType.KPI_SUGGESTION_ASSIST, prompt, tenant_id)

    try:
        data = extract_json_object(resp.text)
    except LLMJsonParseError as exc:
        raise ValueError(f"LLM output not valid JSON: {exc}") from exc

    raw_list = data.get("suggestions")
    if not isinstance(raw_list, list):
        raise ValueError("missing suggestions array")

    adapter = TypeAdapter(list[Nis2KritisKpiSuggestion])
    suggestions = adapter.validate_python(raw_list)

    seen: set[Nis2KritisKpiType] = set()
    deduped: list[Nis2KritisKpiSuggestion] = []
    for s in suggestions:
        if s.kpi_type in seen:
            continue
        seen.add(s.kpi_type)
        deduped.append(s)

    for kt in Nis2KritisKpiType:
        if kt not in seen:
            deduped.append(
                Nis2KritisKpiSuggestion(
                    kpi_type=kt,
                    suggested_value_percent=0,
                    confidence=0.2,
                    rationale="Kein belastbarer Hinweis im Modell-Output – bitte manuell bewerten.",
                ),
            )

    return Nis2KritisKpiSuggestionResponse(
        ai_system_id=ai_system.id,
        suggestions=sorted(deduped, key=lambda x: x.kpi_type.value),
    )
