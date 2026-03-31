"""Kombinierter Markdown-Export: Systemprofil, KPIs, Maßnahmen, AI-Act-Sektionen."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.ai_act_doc_models import AIActDocSectionKey
from app.ai_system_models import AISystem
from app.classification_models import RiskClassification
from app.nis2_kritis_models import Nis2KritisKpi
from app.repositories.ai_act_docs import AIActDocRepository
from app.services.ai_act_docs import default_section_title

if TYPE_CHECKING:
    from app.ai_governance_action_models import AIGovernanceActionRead


def render_ai_act_documentation_markdown(
    *,
    system: AISystem,
    classification: RiskClassification | None,
    nis2_kpis: list[Nis2KritisKpi],
    actions: list[AIGovernanceActionRead],
    evidence_count: int,
    docs_repo: AIActDocRepository,
    tenant_id: str,
) -> str:
    lines: list[str] = [
        "# EU AI Act – Technische Dokumentation (Entwurf)",
        "",
        f"**KI-System:** {system.name} (`{system.id}`)",
        f"**Business Unit:** {system.business_unit}",
        f"**Risk Level:** {system.risk_level}",
        f"**AI-Act-Kategorie:** {system.ai_act_category}",
        f"**Evidenz-Anhänge (Anzahl):** {evidence_count}",
        "",
        "## Profil",
        "",
        system.description,
        "",
    ]
    if classification:
        rat = (classification.classification_rationale or "").strip()
        lines += [
            "## Klassifikation",
            "",
            f"- Risiko: {classification.risk_level}",
            f"- Pfad: {classification.classification_path}",
            f"- Annex-III-Kategorie: {classification.annex_iii_category}",
            "",
            rat or "_Keine Begründung hinterlegt._",
            "",
        ]

    lines += ["## NIS2 / KRITIS KPIs", ""]
    if not nis2_kpis:
        lines.append("_Keine KPI-Zeilen._")
    else:
        for k in nis2_kpis:
            lines.append(f"- **{k.kpi_type.value}:** {k.value_percent}%")
    lines.append("")

    lines += ["## Governance-Maßnahmen (Auszug)", ""]
    rel = [a for a in actions if a.related_ai_system_id == system.id]
    if not rel:
        lines.append("_Keine verknüpften Maßnahmen._")
    else:
        for a in rel[:25]:
            lines.append(
                f"- **{a.title}** – {a.status} – {a.related_requirement}"
                + (f" – fällig {a.due_date.date()}" if a.due_date else ""),
            )
    lines.append("")

    lines += ["## AI-Act-Dokumentationssektionen", ""]
    stored = {d.section_key: d for d in docs_repo.list_for_system(tenant_id, system.id)}
    for key in AIActDocSectionKey:
        doc = stored.get(key)
        title = doc.title if doc else default_section_title(key)
        lines.append(f"### {title} (`{key.value}`)")
        lines.append("")
        if doc and (doc.content_markdown or "").strip():
            lines.append(doc.content_markdown.strip())
        else:
            lines.append("_Noch nicht befüllt._")
        lines.append("")

    return "\n".join(lines).strip() + "\n"
