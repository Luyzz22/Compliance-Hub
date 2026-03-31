"""
Consolidated prompt builder for readiness-score LLM explain.

Uses only `governance_maturity_contract` for terminology, schema text, version, regulatory line.
"""

from __future__ import annotations

import json
from typing import Any

from app.governance_maturity_contract import (
    GOVERNANCE_MATURITY_CONTRACT_VERSION,
    readiness_explain_json_schema_instructions,
    regulatory_context_standard,
    terminology_contract_for_llm_prompt,
)

_AUDIENCE_PREFIX = (
    "Du bist ein Compliance-Assistenzmodell für deutschsprachige Board- und CISO-Audienz "
    "(DACH). Antworte nur mit gültigem JSON gemäß Schema — kein Markdown, keine Einleitung.\n\n"
)


def build_readiness_explain_prompt(*, facts_envelope: dict[str, Any]) -> str:
    """
    Full prompt: contract version, terminology, schema, regulatory context, facts JSON.

    `facts_envelope`: readiness snapshot, operational_ai_monitoring, governance_activity.
    """
    facts = json.dumps(facts_envelope, ensure_ascii=False)
    return (
        _AUDIENCE_PREFIX
        + f"Explain-Contract-Version: {GOVERNANCE_MATURITY_CONTRACT_VERSION}\n\n"
        + terminology_contract_for_llm_prompt()
        + "\n"
        + readiness_explain_json_schema_instructions()
        + "\n"
        + regulatory_context_standard()
        + "\n\n"
        "Nutze ausschließlich die nachfolgenden JSON-Fakten; erfinde keine Zahlen, Mandanten "
        "oder KI-Systeme.\n\n"
        "JSON-Fakten:\n" + facts
    )
