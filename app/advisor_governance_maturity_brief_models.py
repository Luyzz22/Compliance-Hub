"""Advisor governance maturity brief: Board `GovernanceMaturitySummary` plus triage fields."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.governance_maturity_contract import EXPLAIN_LIST_ITEM_MAX_CHARS, EXPLAIN_LIST_MAX_ITEMS
from app.governance_maturity_summary_models import GovernanceMaturitySummary


class AdvisorGovernanceMaturityBrief(BaseModel):
    """
    Mandanten-Kurzbrief für Berater.

    `governance_maturity_summary` ist dieselbe Struktur wie im Board-Report (Enums, Treiber,
    Slices). Zusätzliche Felder liefern Priorisierung und Mandantenkommunikation.
    """

    governance_maturity_summary: GovernanceMaturitySummary
    recommended_focus_areas: list[str] = Field(
        default_factory=list,
        description="Kurze Hinweise für Mandantenbetreuung (z. B. niedriges OAMI).",
    )
    suggested_next_steps_window: str = Field(
        default="nächste 90 Tage",
        max_length=120,
        description="Zeithorizont für empfohlene Schritte (freier Kurztext, z. B. Quartal).",
    )
    client_ready_paragraph_de: str | None = Field(
        default=None,
        max_length=600,
        description="Optional: 1–2 Sätze für direkte Weitergabe an Mandanten (ohne interne Codes).",
    )

    @field_validator("recommended_focus_areas")
    @classmethod
    def _normalize_focus(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for item in v[:EXPLAIN_LIST_MAX_ITEMS]:
            s = str(item).strip()[:EXPLAIN_LIST_ITEM_MAX_CHARS]
            if s:
                out.append(s)
        return out

    @field_validator("suggested_next_steps_window")
    @classmethod
    def _trim_window(cls, v: str) -> str:
        return (v or "nächste 90 Tage").strip()[:120] or "nächste 90 Tage"


class AdvisorGovernanceMaturityBriefParseResult(BaseModel):
    brief: AdvisorGovernanceMaturityBrief
    parse_ok: bool = True
    used_llm_client_paragraph: bool = False


def advisor_brief_focus_marker_de(brief: AdvisorGovernanceMaturityBrief) -> str:
    """Kurzmarke für Portfolio-Zeilen (aus strukturierten Feldern, nicht aus Freitext-Layout)."""
    if brief.recommended_focus_areas:
        raw = brief.recommended_focus_areas[0].strip()
        if len(raw) > 44:
            raw = raw[:41] + "…"
        return f"Fokus: {raw}"
    lvl = brief.governance_maturity_summary.overall_assessment.level
    return f"Gesamt: {lvl}"


def advisor_brief_portfolio_tooltip_de(brief: AdvisorGovernanceMaturityBrief) -> str:
    """Hover-Text: Gesamtniveau + bis zu drei Fokuszeilen."""
    oa = brief.governance_maturity_summary.overall_assessment
    lines = [
        f"Gesamtbild (konservativ): {oa.level}.",
        *brief.recommended_focus_areas[:3],
    ]
    if brief.suggested_next_steps_window:
        lines.append(f"Zeithorizont: {brief.suggested_next_steps_window}")
    return " ".join(lines)[:500]
