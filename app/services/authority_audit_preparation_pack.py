from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.authority_audit_preparation_pack_models import (
    AuthorityAuditPreparationPackResponse,
    PreparationPackFocus,
    PreparationPackSection,
)
from app.enterprise_control_center_models import ControlCenterSeverity
from app.repositories.ai_inventory import AISystemInventoryRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.compliance_deadlines import ComplianceDeadlineRepository
from app.repositories.nis2_incidents import NIS2IncidentRepository
from app.services.ai_compliance_board_report import list_ai_compliance_board_reports
from app.services.enterprise_control_center import build_enterprise_control_center


def build_authority_audit_preparation_pack(
    *,
    tenant_id: str,
    session: Session,
    focus: PreparationPackFocus,
    audit_repo: AuditLogRepository,
    incident_repo: NIS2IncidentRepository,
    deadline_repo: ComplianceDeadlineRepository,
    ai_repo: AISystemRepository,
    inventory_repo: AISystemInventoryRepository,
) -> AuthorityAuditPreparationPackResponse:
    now = datetime.now(UTC)
    cc = build_enterprise_control_center(
        tenant_id=tenant_id,
        session=session,
        audit_repo=audit_repo,
        incident_repo=incident_repo,
        deadline_repo=deadline_repo,
        ai_repo=ai_repo,
        include_markdown=False,
    )
    urgent = cc.top_urgent_items
    critical = [i for i in urgent if i.severity == ControlCenterSeverity.critical]

    latest_audit = next(iter(audit_repo.list_for_tenant(tenant_id, limit=1)), None)
    audit_ready = latest_audit is not None

    open_incidents = [
        i
        for i in incident_repo.list_for_tenant(tenant_id, limit=100)
        if i.workflow_status.value != "closed"
    ]
    due_deadlines = [
        d
        for d in deadline_repo.list_for_tenant(tenant_id, limit=100)
        if d.escalation_level.value in {"overdue", "critical", "warning"}
    ]
    systems = ai_repo.list_for_tenant(tenant_id)
    register = inventory_repo.posture_summary(tenant_id, total_systems=len(systems))
    board_reports = list_ai_compliance_board_reports(session, tenant_id, limit=1)

    sec_a = PreparationPackSection(
        title_de="A. Executive Compliance Posture Snapshot",
        summary_de=(
            f"Offene Governance-Punkte: {cc.summary_counts.total_open}, "
            f"davon kritisch: {cc.summary_counts.critical}. Fokus={focus.value}."
        ),
        evidence_items=[
            "Enterprise Control Center Summary",
            f"Top-urgente Punkte: {len(urgent)}",
        ],
        missing_items=(
            []
            if cc.summary_counts.critical == 0
            else ["Kritische Punkte vor Termin priorisiert schließen"]
        ),
        due_items=[f"{i.title} ({i.severity.value})" for i in urgent[:3]],
    )

    sec_b = PreparationPackSection(
        title_de="B. Open Critical Items / Missing Evidence",
        summary_de=(
            "Kritische offene Punkte und fehlende Nachweise fuer "
            "Audit-/Behoerdenvorbereitung."
        ),
        evidence_items=[f"{i.title} -> {i.action_label}" for i in critical[:8]],
        missing_items=[i.summary_de for i in critical[:8]],
        due_items=[],
    )

    sec_c = PreparationPackSection(
        title_de="C. Audit Trail Readiness",
        summary_de=(
            "Auditspur ist vorhanden und nachvollziehbar."
            if audit_ready
            else "Keine aktuelle Auditspur vorhanden; Auditfaehigkeit ist eingeschraenkt."
        ),
        evidence_items=(
            [
                f"Letztes Audit-Event: {latest_audit.action} "
                f"({latest_audit.created_at_utc.isoformat()})"
            ]
            if latest_audit
            else []
        ),
        missing_items=(
            []
            if audit_ready
            else ["Governance-relevante Ereignisse muessen auditierbar protokolliert werden"]
        ),
        due_items=[],
    )

    sec_d = PreparationPackSection(
        title_de="D. NIS2 Incident & Deadline Status",
        summary_de=(
            f"Offene NIS2-Incidents: {len(open_incidents)}; "
            f"fristrelevante Kalendereintraege: {len(due_deadlines)}."
        ),
        evidence_items=[
            f"Incident: {i.title} ({i.workflow_status.value})" for i in open_incidents[:8]
        ],
        missing_items=[],
        due_items=[
            f"{d.title} ({d.due_date.isoformat()}, {d.escalation_level.value})"
            for d in due_deadlines[:8]
        ],
    )

    sec_e = PreparationPackSection(
        title_de="E. AI Act / KI-Register / Authority Export Status",
        summary_de=(
            f"KI-Register-Posture: registered={register.registered}, planned={register.planned}, "
            f"partial={register.partial}, unknown={register.unknown}."
        ),
        evidence_items=[
            f"AI-Systeme gesamt: {len(systems)}",
            "Authority-Export ueber dedizierten Endpoint verfuegbar",
        ],
        missing_items=(
            ["KI-Register-Status fuer unbekannte Systeme klaeren"]
            if register.unknown > 0
            else []
        ),
        due_items=[],
    )

    sec_f = PreparationPackSection(
        title_de="F. Recommended Next Preparation Actions",
        summary_de=(
            "Empfohlene naechste Schritte fuer Audit-/Behoerdenvorbereitung "
            "(operativ, nicht-rechtlich)."
        ),
        evidence_items=[],
        missing_items=[],
        due_items=[
            "Kritische Control-Center-Punkte zuerst schliessen",
            "Aktuellsten Authority-Export vor Terminlauf erzeugen",
            "Board-Readiness mit aktuellem Reportstand absichern",
        ],
    )
    if not board_reports:
        sec_f.due_items.append("Board-Report erzeugen und Freigabestatus dokumentieren")

    markdown_lines = [
        "# Authority & Audit Preparation Pack (Arbeitsstand)",
        "",
        f"- Mandant: {tenant_id}",
        f"- Zeitpunkt (UTC): {now.isoformat()}",
        f"- Fokus: {focus.value}",
        "- Hinweis: Operative Vorbereitungshilfe, keine Rechtsberatung.",
        "",
        "## A) Executive Posture",
        sec_a.summary_de,
        "",
        "## B) Kritische offene Punkte",
    ]
    for row in sec_b.evidence_items[:10]:
        markdown_lines.append(f"- {row}")
    markdown_lines.extend(
        [
            "",
            "## C) Audit Trail",
            sec_c.summary_de,
            "",
            "## D) NIS2/Fristen",
            sec_d.summary_de,
            "",
            "## E) AI Act / Register / Export",
            sec_e.summary_de,
            "",
            "## F) Nächste Schritte",
        ]
    )
    for action in sec_f.due_items:
        markdown_lines.append(f"- {action}")

    return AuthorityAuditPreparationPackResponse(
        tenant_id=tenant_id,
        generated_at_utc=now,
        focus=focus,
        source_sections=[
            "enterprise_control_center",
            "audit_log",
            "nis2_incidents",
            "compliance_calendar",
            "ai_inventory_register",
            "board_reports",
        ],
        section_a_executive_posture=sec_a,
        section_b_open_critical_missing_evidence=sec_b,
        section_c_audit_trail_readiness=sec_c,
        section_d_nis2_incident_deadline_status=sec_d,
        section_e_ai_act_register_authority_status=sec_e,
        section_f_recommended_next_preparation_actions=sec_f,
        top_urgent_items=urgent,
        markdown_de="\n".join(markdown_lines).strip() + "\n",
    )
