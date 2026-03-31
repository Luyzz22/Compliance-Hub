"""
Language-agnostic API contract for governance maturity levels (aligned with frontend).

**Single source of truth** for:
- API enums used in JSON (LLM + REST)
- German labels injected into LLM prompts (mirrors UI copy; canonical UI strings live in TS)
- Explain-schema version string for prompts and change tracking
- Readiness- und OAMI-Index-Bänder für Regression (`contract_full_mapping_snapshot`,
  `contract_full_oami_mapping_snapshot`)

Frontend mirror: frontend/src/lib/governanceMaturityTypes.ts
German presentation (UI): frontend/src/lib/governanceMaturityDeCopy.ts
Human doc: docs/governance-maturity-copy-contract.md

All LLM structured JSON must use **API level strings** only:
(basic | managed | embedded) and (low | medium | high), never ad-hoc synonyms.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final, Literal

# Bump when JSON shape or enum sets change (keep in sync with docs + frontend types).
GOVERNANCE_MATURITY_CONTRACT_VERSION: Final[str] = "3"

# --- Explain payload limits (single source for parser + doc) ---
EXPLAIN_LIST_MAX_ITEMS: Final[int] = 5
EXPLAIN_LIST_ITEM_MAX_CHARS: Final[int] = 200

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


def derive_readiness_level_from_score(score: int) -> ReadinessLevelLiteral:
    """
    Band mapping used by Readiness Score service (documentation + tests).
    Not a second runtime source: server `ReadinessScoreResponse.level` is authoritative
    for explain alignment.
    """
    s = max(0, min(100, int(score)))
    if s < 45:
        return "basic"
    if s < 70:
        return "managed"
    return "embedded"


def derive_oami_level_from_index(index: int) -> IndexLevelLiteral:
    """
    OAMI-Index (0–100) → API-Level; gleiche Bänder wie
    ``operational_monitoring_index._level_from_index``.

    Kalibrierung: ``docs/governance-operational-ai-monitoring.md``.
    Für Tests und Mapping-Snapshots; serverseitiges OAMI-Level bleibt im Explain-Flow autoritativ.
    """
    s = max(0, min(100, int(index)))
    if s < 40:
        return "low"
    if s < 70:
        return "medium"
    return "high"


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


def contract_mapping_for_tests() -> dict[str, object]:
    """Stable snapshot for unit tests (ordering deterministic)."""
    return {
        "contract_version": GOVERNANCE_MATURITY_CONTRACT_VERSION,
        "readiness_api_levels": list(READINESS_API_LEVELS),
        "readiness_level_de": {k: READINESS_LEVEL_DE[k] for k in READINESS_API_LEVELS},
        "index_api_levels": list(INDEX_API_LEVELS),
        "index_level_de": {k: INDEX_LEVEL_DE[k] for k in INDEX_API_LEVELS},
    }


def contract_full_mapping_snapshot() -> dict[str, object]:
    """
    Full mapping for regression: enums, DE labels, readiness score bands (documentation bands).

    Checked against ``tests/fixtures/governance_maturity_mapping_snapshot.json`` — update that
    file intentionally when bands or labels change.
    """
    base = contract_mapping_for_tests()
    bands: list[dict[str, object]] = [
        {
            "score_min": 0,
            "score_max_exclusive": 45,
            "level": ReadinessLevelApi.BASIC.value,
            "label_de": READINESS_LEVEL_DE[ReadinessLevelApi.BASIC.value],
        },
        {
            "score_min": 45,
            "score_max_exclusive": 70,
            "level": ReadinessLevelApi.MANAGED.value,
            "label_de": READINESS_LEVEL_DE[ReadinessLevelApi.MANAGED.value],
        },
        {
            "score_min": 70,
            "score_max_exclusive": 101,
            "level": ReadinessLevelApi.EMBEDDED.value,
            "label_de": READINESS_LEVEL_DE[ReadinessLevelApi.EMBEDDED.value],
        },
    ]
    return {**base, "readiness_score_bands": bands}


def contract_full_oami_mapping_snapshot() -> dict[str, object]:
    """
    OAMI-Index-Bänder → API-Level → DE-Label (Regression).

    Checked against ``tests/fixtures/governance_maturity_oami_mapping_snapshot.json`` — update that
    file intentionally when bands or labels change.
    """
    return {
        "contract_version": GOVERNANCE_MATURITY_CONTRACT_VERSION,
        "source": "app.services.operational_monitoring_index._level_from_index",
        "index_api_levels": list(INDEX_API_LEVELS),
        "index_level_de": {k: INDEX_LEVEL_DE[k] for k in INDEX_API_LEVELS},
        "oami_index_bands": [
            {
                "index_min": 0,
                "index_max_exclusive": 40,
                "level": GovernanceActivityLevelApi.LOW.value,
                "label_de": INDEX_LEVEL_DE[GovernanceActivityLevelApi.LOW.value],
            },
            {
                "index_min": 40,
                "index_max_exclusive": 70,
                "level": GovernanceActivityLevelApi.MEDIUM.value,
                "label_de": INDEX_LEVEL_DE[GovernanceActivityLevelApi.MEDIUM.value],
            },
            {
                "index_min": 70,
                "index_max_exclusive": 101,
                "level": GovernanceActivityLevelApi.HIGH.value,
                "label_de": INDEX_LEVEL_DE[GovernanceActivityLevelApi.HIGH.value],
            },
        ],
    }


def regulatory_context_standard() -> str:
    """Short regulatory framing for LLM prompts (no article citations)."""
    return (
        "Regulatorischer Kontext (knapp, ohne Paragraphen): EU AI Act, NIS2, "
        "ISO/IEC 42001 (KI-Managementsystem), ISO/IEC 27001 (ISMS)."
    )


def readiness_api_level_list_for_prompt() -> str:
    return " | ".join(READINESS_API_LEVELS)


def index_api_level_list_for_prompt() -> str:
    return " | ".join(INDEX_API_LEVELS)


def readiness_mapping_lines_for_prompt() -> str:
    lines = [
        f"  - {api} → UI-Bezeichnung „{READINESS_LEVEL_DE[api]}“" for api in READINESS_API_LEVELS
    ]
    return "\n".join(lines)


def index_mapping_lines_for_prompt() -> str:
    lines = [f"  - {api} → UI-Bezeichnung „{INDEX_LEVEL_DE[api]}“" for api in INDEX_API_LEVELS]
    return "\n".join(lines)


def oami_event_subtype_context_for_prompt() -> str:
    """
    Kurz: OAMI nutzt weiter nur level low|medium|high; Subtype-Kategorien nur zur Einordnung.
    """
    return (
        "OAMI-Laufzeitdaten: optionaler technischer ``event_subtype`` pro Incident oder "
        "Metrikalarm (z. B. safety_violation, availability_incident, drift_high). "
        "Sicherheitsnahe Subtypes werden im Index stärker gewichtet als reine "
        "Verfügbarkeit — ohne konkrete Gewichtszahlen zu nennen. "
        "JSON-Feld ``level`` für OAMI bleibt ausschließlich low | medium | high."
    )


def terminology_contract_for_llm_prompt() -> str:
    """
    Instruct the model: JSON `level` fields = API enums only; narrative without invented
    stage names. Built from mapping dicts (no duplicate hard-coded German strings outside
    READINESS_LEVEL_DE / INDEX_LEVEL_DE).
    """
    return (
        f"Governance-Maturity-Explain Schema-Version: {GOVERNANCE_MATURITY_CONTRACT_VERSION}\n"
        "Terminologie (verbindlich):\n"
        "- AI & Compliance Readiness — API-Werte für JSON-Feld level (nur eines davon):\n"
        f"  {readiness_api_level_list_for_prompt()}\n"
        f"{readiness_mapping_lines_for_prompt()}\n"
        "- Governance-Aktivitätsindex (GAI) und Operativer KI-Monitoring-Index (OAMI) — "
        "API-Werte für JSON-Feld level (nur eines davon):\n"
        f"  {index_api_level_list_for_prompt()}\n"
        f"{index_mapping_lines_for_prompt()}\n"
        "Im JSON sind ausschließlich diese englischen API-Werte in den Feldern `level` erlaubt — "
        "keine Synonyme (z. B. nicht „advanced“ statt embedded).\n"
        "Alle Freitext-Felder auf Deutsch; keine neuen Akronyme für Readiness/GAI/OAMI erfinden.\n"
        "In Fließtext-Feldern: keine eigenen Synonyme für Stufen; "
        "Ursachen und Maßnahmen sachlich.\n" + oami_event_subtype_context_for_prompt() + "\n"
    )


def readiness_explain_json_schema_instructions() -> str:
    """Expected JSON shape for readiness explain LLM (single object, no markdown)."""
    rl = " | ".join(f'"{x}"' for x in READINESS_API_LEVELS)
    il = " | ".join(f'"{x}"' for x in INDEX_API_LEVELS)
    return (
        "Antworte ausschließlich mit **einem** JSON-Objekt "
        "(kein Markdown, keine Codefences). Schema:\n"
        "{\n"
        '  "readiness_explanation": {\n'
        '    "score": <integer 0-100>,\n'
        f'    "level": {rl}  (im JSON genau ein String-Wert),\n'
        '    "short_reason": "<1-3 Sätze Deutsch>",\n'
        '    "drivers_positive": ["<kurz>", "..."],\n'
        '    "drivers_negative": ["<kurz>", "..."],\n'
        '    "regulatory_focus": "<1 Satz>"\n'
        "  },\n"
        '  "operational_monitoring_explanation": null | {\n'
        '    "index": <integer 0-100 oder null>,\n'
        f'    "level": null | {il}  (im JSON ein String oder null),\n'
        '    "recent_incidents_summary": "<kurz Deutsch oder leer>",\n'
        '    "monitoring_gaps": ["<kurz>", "..."],\n'
        '    "improvement_suggestions": ["<kurz>", "..."]\n'
        "  }\n"
        "}\n"
        "Wenn keine OAMI-Daten im Kontext: setze operational_monitoring_explanation auf null.\n"
        f"Listen: höchstens je {EXPLAIN_LIST_MAX_ITEMS} Einträge, je Eintrag höchstens "
        f"{EXPLAIN_LIST_ITEM_MAX_CHARS} Zeichen.\n"
    )


def governance_maturity_board_summary_json_schema_instructions() -> str:
    """
    Expected JSON shape for Board governance maturity executive summary (single object).

    Top-level keys: structured `governance_maturity_summary` plus
    `executive_overview_governance_maturity_de` paragraph. API enums only inside JSON `level`
    fields; paragraph must not spell UI labels (Basis/Etabliert/Integriert, Niedrig/Mittel/Hoch).
    """
    rl = " | ".join(f'"{x}"' for x in READINESS_API_LEVELS)
    il = " | ".join(f'"{x}"' for x in INDEX_API_LEVELS)
    return (
        "Antworte ausschließlich mit **einem** JSON-Objekt "
        "(kein Markdown, keine Codefences). Schema:\n"
        "{\n"
        '  "governance_maturity_summary": {\n'
        '    "readiness": {\n'
        '      "score": <integer 0-100>,\n'
        f'      "level": {rl},\n'
        '      "short_reason": "<1-3 Sätze Deutsch; relative Einordnung; '
        'keine UI-Stufenbezeichnungen>"\n'
        "    },\n"
        '    "activity": {\n'
        '      "index": <integer 0-100>,\n'
        f'      "level": {il},\n'
        '      "short_reason": "<1-3 Sätze Deutsch; Nutzung/Steuerungsaktivität; '
        'keine UI-Stufenbezeichnungen>"\n'
        "    },\n"
        '    "operational_monitoring": {\n'
        '      "index": <integer 0-100 oder null wenn kein Laufzeit-Monitoring sichtbar>,\n'
        f'      "level": null | {il},\n'
        '      "short_reason": "<1-3 Sätze Deutsch; operative Sicht; '
        'keine UI-Stufenbezeichnungen>"\n'
        "    },\n"
        '    "overall_assessment": {\n'
        f'      "level": {il},\n'
        '      "short_summary": "<2-4 Sätze Deutsch; Gesamtbild für Vorstand/Aufsicht>",\n'
        f'      "key_risks": ["<kurz>", "..."],\n'
        f'      "key_strengths": ["<kurz>", "..."]\n'
        "    }\n"
        "  },\n"
        '  "executive_overview_governance_maturity_de": '
        '"<genau 3-5 vollständige Sätze Deutsch; Vorstand/Aufsicht; sachlich, nicht technisch; '
        'keine UI-Labels für Stufen; keine neuen Akronyme; keine Zitate von Normtexten>"\n'
        "}\n"
        f"Listen key_risks/key_strengths: je höchstens {EXPLAIN_LIST_MAX_ITEMS} Einträge, "
        f"je Eintrag höchstens {EXPLAIN_LIST_ITEM_MAX_CHARS} Zeichen.\n"
        "Feld `executive_overview_governance_maturity_de` ist Pflicht und muss mindestens "
        "80 Zeichen enthalten.\n"
    )


# Advisor-Brief: JSON-Shape-Version (unabhängig von GOVERNANCE_MATURITY_CONTRACT_VERSION).
ADVISOR_GOVERNANCE_MATURITY_BRIEF_SCHEMA_VERSION: Final[str] = "1"


def advisor_governance_maturity_brief_json_schema_instructions() -> str:
    """
    JSON-Objekt für Berater-Kurzbrief: gleicher Block `governance_maturity_summary` wie Board,
    plus advisor-spezifische Felder (kein Vorstands-Fließtext-Pflichtfeld).
    """
    rl = " | ".join(f'"{x}"' for x in READINESS_API_LEVELS)
    il = " | ".join(f'"{x}"' for x in INDEX_API_LEVELS)
    return (
        "Antworte ausschließlich mit **einem** JSON-Objekt (kein Markdown, keine Codefences). "
        "Schema:\n"
        "{\n"
        '  "governance_maturity_summary": {\n'
        '    "readiness": {\n'
        '      "score": <integer 0-100>,\n'
        f'      "level": {rl},\n'
        '      "short_reason": "<1-3 Sätze Deutsch; keine UI-Stufenbezeichnungen>"\n'
        "    },\n"
        '    "activity": {\n'
        '      "index": <integer 0-100>,\n'
        f'      "level": {il},\n'
        '      "short_reason": "<1-3 Sätze Deutsch; Steuerungsnutzung>"\n'
        "    },\n"
        '    "operational_monitoring": {\n'
        '      "index": <integer 0-100 oder null>,\n'
        f'      "level": null | {il},\n'
        '      "short_reason": "<1-3 Sätze Deutsch; operative Sicht>"\n'
        "    },\n"
        '    "overall_assessment": {\n'
        f'      "level": {il},\n'
        '      "short_summary": "<2-3 Sätze Deutsch; Berater-Perspektive: Priorisierung>",\n'
        f'      "key_risks": ["<kurz>", "..."],\n'
        f'      "key_strengths": ["<kurz>", "..."]\n'
        "    }\n"
        "  },\n"
        '  "recommended_focus_areas": '
        '["<z. B. OAMI niedrig – Monitoring ausbauen>", "..."],\n'
        '  "suggested_next_steps_window": "<z. B. nächste 90 Tage>",\n'
        '  "client_ready_paragraph_de": '
        '"<optional null oder 1-2 Sätze Deutsch; sachlich; geeignet zur Weitergabe an Mandant>"\n'
        "}\n"
        f"recommended_focus_areas: höchstens {EXPLAIN_LIST_MAX_ITEMS} Einträge, "
        f"je höchstens {EXPLAIN_LIST_ITEM_MAX_CHARS} Zeichen.\n"
        "Feld `client_ready_paragraph_de` ist optional; wenn gesetzt, höchstens 600 Zeichen, "
        "ohne interne Produktcodes.\n"
    )
