"""Markdown-Abschnitt für Advisor Governance-Maturity-Brief (Steckbrief, Snapshot-Export)."""

from __future__ import annotations

from app.advisor_governance_maturity_brief_models import AdvisorGovernanceMaturityBrief
from app.governance_maturity_summary_models import GovernanceMaturitySummary


def render_advisor_governance_maturity_brief_markdown_section(
    brief: AdvisorGovernanceMaturityBrief,
) -> str:
    """Kurzblock für Mandantenkommunikation (ohne interne Produktcodes im Fließtext)."""
    gm: GovernanceMaturitySummary = brief.governance_maturity_summary
    oa = gm.overall_assessment
    bullets = (
        "\n".join(f"- {a}" for a in brief.recommended_focus_areas)
        or "- Keine zusätzlichen Fokuspunkte."
    )
    client = ""
    if brief.client_ready_paragraph_de:
        client = f"\n{brief.client_ready_paragraph_de.strip()}\n"

    return f"""## Governance-Reife – Kurzüberblick

**Gesamtbild (konservativ):** {oa.level}

{oa.short_summary.strip()}

**Empfohlene Fokusbereiche**

{bullets}

**Vorgeschlagener Zeithorizont:** {brief.suggested_next_steps_window}
{client}"""
