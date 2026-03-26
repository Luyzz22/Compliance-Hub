"""
Language-agnostic API contract for governance maturity levels (aligned with frontend).

Frontend mirror: frontend/src/lib/governanceMaturityTypes.ts
German presentation (UI only): frontend/src/lib/governanceMaturityDeCopy.ts

All LLM prompts and structured JSON must use **API level strings** only
(basic | managed | embedded) and (low | medium | high), never ad-hoc synonyms.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

# --- API values (identical to TypeScript READINESS_LEVEL_API_VALUES / INDEX_LEVEL_API_VALUES)


class ReadinessLevelApi(StrEnum):
    BASIC = "basic"
    MANAGED = "managed"
    EMBEDDED = "embedded"


class GovernanceActivityLevelApi(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OperationalMonitoringLevelApi(StrEnum):
    """Same scale as GAI; distinct type for documentation/clarity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


ReadinessLevelLiteral = Literal["basic", "managed", "embedded"]
IndexLevelLiteral = Literal["low", "medium", "high"]

READINESS_API_LEVELS: tuple[str, ...] = tuple(m.value for m in ReadinessLevelApi)
INDEX_API_LEVELS: tuple[str, ...] = tuple(m.value for m in GovernanceActivityLevelApi)

# German labels (Board copy); must stay in sync with governanceMaturityDeCopy.ts
READINESS_LEVEL_DE: dict[str, str] = {
    ReadinessLevelApi.BASIC.value: "Basis",
    ReadinessLevelApi.MANAGED.value: "Etabliert",
    ReadinessLevelApi.EMBEDDED.value: "Integriert",
}

INDEX_LEVEL_DE: dict[str, str] = {
    GovernanceActivityLevelApi.LOW.value: "Niedrig",
    GovernanceActivityLevelApi.MEDIUM.value: "Mittel",
    GovernanceActivityLevelApi.HIGH.value: "Hoch",
}


def readiness_level_de(api: str) -> str:
    """German label for prompts; falls back to API string if unknown."""
    return READINESS_LEVEL_DE.get(str(api).strip().lower(), str(api))


def index_level_de(api: str | None) -> str:
    if api is None or str(api).strip() == "":
        return "–"
    k = str(api).strip().lower()
    return INDEX_LEVEL_DE.get(k, str(api))


def normalize_readiness_level(raw: object) -> ReadinessLevelLiteral | None:
    if raw is None:
        return None
    v = str(raw).strip().lower()
    if v in READINESS_API_LEVELS:
        return v  # type: ignore[return-value]
    return None


def normalize_index_level(raw: object) -> IndexLevelLiteral | None:
    if raw is None:
        return None
    v = str(raw).strip().lower()
    if v in INDEX_API_LEVELS:
        return v  # type: ignore[return-value]
    return None


def terminology_contract_for_llm_prompt() -> str:
    """
    Instruct the model: fixed German *display* names for reference in narrative,
    but JSON `level` fields must use API enums only.
    """
    return (
        "Terminologie (verbindlich, keine alternativen Stufenbezeichnungen erfinden):\n"
        "- AI & Compliance Readiness: API-Level basic | managed | embedded entsprechen "
        "den UI-Bezeichnungen Basis | Etabliert | Integriert.\n"
        "- Governance-Aktivitätsindex (GAI) und Operativer KI-Monitoring-Index (OAMI): "
        "API-Level low | medium | high entsprechen Niedrig | Mittel | Hoch.\n"
        "Im JSON sind ausschließlich die englischen API-Werte (basic, managed, embedded, "
        "low, medium, high) in den Feldern `level` erlaubt.\n"
        "Regulatorischer Rahmen (kurz, konsistent): EU AI Act, NIS2, ISO/IEC 42001, "
        "ISO/IEC 27001 — ohne Paragraphenzitate, ohne neue Akronyme für die Indizes.\n"
        "In Fließtext-Feldern: keine eigenen Synonyme für diese Stufen (z. B. nicht "
        "„fortgeschritten“ statt Etabliert/integriert); Ursachen und Maßnahmen sachlich "
        "beschreiben.\n"
    )


def readiness_explain_json_schema_instructions() -> str:
    """Exact JSON shape expected from the readiness explain LLM (single object, no markdown)."""
    return (
        "Antworte ausschließlich mit **einem** JSON-Objekt "
        "(kein Markdown, keine Codefences). Schema:\n"
        "{\n"
        '  "readiness_explanation": {\n'
        '    "score": <integer 0-100>,\n'
        '    "level": "basic" | "managed" | "embedded",\n'
        '    "short_reason": "<1-3 Sätze Deutsch, ohne alternative Stufenlabels>",\n'
        '    "drivers_positive": ["<kurz>", "..."],\n'
        '    "drivers_negative": ["<kurz>", "..."],\n'
        '    "regulatory_focus": "<1 Satz: Bezug EU AI Act / NIS2 / ISO 42001/27001>"\n'
        "  },\n"
        '  "operational_monitoring_explanation": null | {\n'
        '    "index": <integer 0-100 oder null>,\n'
        '    "level": "low" | "medium" | "high" | null,\n'
        '    "recent_incidents_summary": "<kurz Deutsch oder leer>",\n'
        '    "monitoring_gaps": ["<kurz>", "..."],\n'
        '    "improvement_suggestions": ["<kurz>", "..."]\n'
        "  }\n"
        "}\n"
        "Wenn keine OAMI-Daten im Kontext: setze operational_monitoring_explanation auf null.\n"
        "listen: höchstens je 5 Einträge, je Eintrag höchstens 200 Zeichen.\n"
    )
