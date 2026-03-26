"""LLM-Prompt: Advisor Governance-Maturity-Brief (JSON, Board-kompatibler Kernblock)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.governance_maturity_contract import (
    ADVISOR_GOVERNANCE_MATURITY_BRIEF_SCHEMA_VERSION,
    GOVERNANCE_MATURITY_CONTRACT_VERSION,
    advisor_governance_maturity_brief_json_schema_instructions,
    regulatory_context_standard,
    terminology_contract_for_llm_prompt,
)
from app.governance_maturity_summary_models import GovernanceMaturitySummary

if TYPE_CHECKING:
    from app.governance_maturity_models import GovernanceMaturityResponse

_ADVISOR_PREFIX = (
    "Du bist ein erfahrener GRC- und AI-Governance-Berater für Mandantenbetreuung im DACH-Raum. "
    "Deine Leser sind Beraterinnen und Berater (Priorisierung, Triaging) und indirekt "
    "Geschäftsführung des Mandanten. Antworte nur mit gültigem JSON gemäß Schema — kein Markdown, "
    "keine Einleitung.\n\n"
)


def build_advisor_governance_maturity_brief_prompt(
    tenant_maturity_snapshot: GovernanceMaturityResponse,
    board_summary: GovernanceMaturitySummary | None,
    *,
    contract_version: str = GOVERNANCE_MATURITY_CONTRACT_VERSION,
    brief_schema_version: str = ADVISOR_GOVERNANCE_MATURITY_BRIEF_SCHEMA_VERSION,
) -> str:
    """
    Baut den vollständigen Prompt inkl. Terminologie, Schema und regulatorischer Zeile.

    `board_summary` ist optional: wenn vorhanden, soll die Ausgabe inhaltlich konsistent bleiben,
    ohne neue Fakten gegenüber Snapshot und Board-Kern zu erfinden.
    """
    snap_json = json.dumps(
        tenant_maturity_snapshot.model_dump(mode="json"),
        ensure_ascii=False,
    )
    board_block = ""
    if board_summary is not None:
        board_block = (
            "\n\nReferenz: bereits erstellter Board-Kern (`governance_maturity_summary`), "
            "nur konsistent weiterverdichten, keine widersprüchlichen Levels oder Scores:\n"
            + json.dumps(
                {"governance_maturity_summary": board_summary.model_dump(mode="json")},
                ensure_ascii=False,
            )
        )
    return (
        _ADVISOR_PREFIX
        + f"Governance-Maturity-Contract-Version: {contract_version}\n"
        + f"Advisor-Governance-Maturity-Brief-Schema-Version: {brief_schema_version}\n\n"
        + terminology_contract_for_llm_prompt()
        + "\n"
        + advisor_governance_maturity_brief_json_schema_instructions()
        + "\n"
        + regulatory_context_standard()
        + "\n\n"
        "Perspektive: Mandantenbetreuung — wo lohnt Beratung, welche Baustellen zuerst?\n"
        "Nutze ausschließlich die JSON-Fakten des Mandanten-Snapshots; score/index/level in den "
        "Fakten sind maßgeblich — Kurzbegründungen und Fokuslisten müssen dazu passen.\n"
        "recommended_focus_areas: konkrete, umsetzbare Kurzhinweise (keine Floskeln).\n"
        "client_ready_paragraph_de: nur wenn sinnvoll; neutral, ohne Personen oder Systemnamen, "
        "geeignet zur E-Mail an den Mandanten.\n\n"
        "JSON-Fakten (Mandanten-Snapshot):\n" + snap_json + board_block
    )
