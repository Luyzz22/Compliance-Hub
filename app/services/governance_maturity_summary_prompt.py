"""Prompt builder: Board governance maturity executive summary (contract v2, JSON + paragraph)."""

from __future__ import annotations

import json

from app.governance_maturity_contract import (
    GOVERNANCE_MATURITY_CONTRACT_VERSION,
    governance_maturity_board_summary_json_schema_instructions,
    regulatory_context_standard,
    terminology_contract_for_llm_prompt,
)
from app.governance_maturity_models import GovernanceMaturityResponse

_AUDIENCE_PREFIX = (
    "Du bist ein erfahrener GRC- und AI-Governance-Berater für Vorstand und Aufsichtsrat im "
    "DACH-Raum. Antworte nur mit gültigem JSON gemäß Schema — kein Markdown, keine Einleitung.\n\n"
)


def build_governance_maturity_summary_prompt(
    tenant_maturity_snapshot: GovernanceMaturityResponse,
    contract_version: str = GOVERNANCE_MATURITY_CONTRACT_VERSION,
) -> str:
    """
    Full prompt: contract version, terminology, schema, regulatory line, maturity JSON facts.

    `contract_version` should match ``GOVERNANCE_MATURITY_CONTRACT_VERSION`` (tests may override).
    """
    facts = json.dumps(
        tenant_maturity_snapshot.model_dump(mode="json"),
        ensure_ascii=False,
    )
    return (
        _AUDIENCE_PREFIX
        + f"Governance-Maturity-Board-Summary-Contract-Version: {contract_version}\n\n"
        + terminology_contract_for_llm_prompt()
        + "\n"
        + governance_maturity_board_summary_json_schema_instructions()
        + "\n"
        + regulatory_context_standard()
        + "\n\n"
        "Nutze ausschließlich die nachfolgenden JSON-Fakten; erfinde keine Zahlen, Mandanten "
        "oder KI-Systeme. Die Felder score/index/level in den Fakten sind maßgeblich — "
        "deine Kurzbegründungen müssen dazu passen.\n\n"
        "JSON-Fakten (Mandanten-Snapshot):\n"
        + facts
    )
