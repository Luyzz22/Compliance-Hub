from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.enterprise_control_center_models import (
    ControlCenterSection,
    ControlCenterSeverity,
    ControlCenterStatus,
    EnterpriseControlCenterItem,
    EnterpriseControlCenterResponse,
    EnterpriseControlCenterSectionGroup,
    EnterpriseControlCenterSummaryCounts,
)
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.compliance_deadlines import ComplianceDeadlineRepository
from app.repositories.nis2_incidents import NIS2IncidentRepository
from app.services.ai_compliance_board_report import list_ai_compliance_board_reports


def _due_status(due_at: datetime, now: datetime) -> ControlCenterStatus:
    if due_at < now:
        return ControlCenterStatus.overdue
    if due_at <= now + timedelta(days=7):
        return ControlCenterStatus.due_soon
    return ControlCenterStatus.open


def _due_severity(due_at: datetime, now: datetime) -> ControlCenterSeverity:
    if due_at < now:
        return ControlCenterSeverity.critical
    if due_at <= now + timedelta(days=7):
        return ControlCenterSeverity.warning
    return ControlCenterSeverity.info


def build_enterprise_control_center(
    *,
    tenant_id: str,
    session: Session,
    audit_repo: AuditLogRepository,
    incident_repo: NIS2IncidentRepository,
    deadline_repo: ComplianceDeadlineRepository,
    ai_repo: AISystemRepository,
    include_markdown: bool,
) -> EnterpriseControlCenterResponse:
    now = datetime.now(UTC)
    items: list[EnterpriseControlCenterItem] = []

    # Audit freshness and export traces
    latest_audit = next(iter(audit_repo.list_for_tenant(tenant_id, limit=1)), None)
    if latest_audit is None:
        items.append(
            EnterpriseControlCenterItem(
                section=ControlCenterSection.audit,
                severity=ControlCenterSeverity.warning,
                status=ControlCenterStatus.blocked,
                title="Keine Governance-Auditspur vorhanden",
                summary_de=(
                    "Für diesen Mandanten wurden noch keine relevanten "
                    "Governance-Ereignisse protokolliert."
                ),
                due_at=None,
                tenant_id=tenant_id,
                source_type="audit_log",
                source_id="none",
                action_label="Audit-Log prüfen",
                action_href="/tenant/audit-log",
            )
        )
    elif latest_audit.created_at_utc.replace(tzinfo=UTC) < now - timedelta(days=30):
        items.append(
            EnterpriseControlCenterItem(
                section=ControlCenterSection.audit,
                severity=ControlCenterSeverity.info,
                status=ControlCenterStatus.open,
                title="Auditspur seit mehr als 30 Tagen unverändert",
                summary_de=(
                    "Bitte prüfen, ob Governance-relevante Prozesse aktuell "
                    "sauber protokolliert werden."
                ),
                due_at=latest_audit.created_at_utc.replace(tzinfo=UTC) + timedelta(days=31),
                tenant_id=tenant_id,
                source_type="audit_log",
                source_id=latest_audit.id,
                action_label="Audit-Log öffnen",
                action_href="/tenant/audit-log",
            )
        )

    # NIS2 incidents and reporting deadlines
    for inc in incident_repo.list_for_tenant(tenant_id, limit=50):
        if inc.workflow_status.value == "closed":
            continue
        for label, due in (
            ("BSI-Frühmeldung", inc.bsi_notification_deadline),
            ("BSI-Bericht", inc.bsi_report_deadline),
            ("Abschlussbericht", inc.final_report_deadline),
        ):
            if due is None:
                continue
            due_utc = due if due.tzinfo else due.replace(tzinfo=UTC)
            items.append(
                EnterpriseControlCenterItem(
                    section=ControlCenterSection.incidents_reporting,
                    severity=_due_severity(due_utc, now),
                    status=_due_status(due_utc, now),
                    title=f"NIS2-Incident: {label} fällig",
                    summary_de=(
                        f"{inc.title} ({inc.incident_type.value}) erfordert "
                        f"{label.lower()} im Workflow-Status {inc.workflow_status.value}."
                    ),
                    due_at=due_utc,
                    tenant_id=tenant_id,
                    source_type="nis2_incident",
                    source_id=inc.id,
                    action_label="Incident öffnen",
                    action_href="/incidents",
                )
            )

    # Compliance calendar deadlines
    for dl in deadline_repo.list_for_tenant(tenant_id, limit=100):
        due_utc = datetime.combine(dl.due_date, datetime.min.time(), tzinfo=UTC)
        status = _due_status(due_utc, now)
        if status not in {ControlCenterStatus.overdue, ControlCenterStatus.due_soon}:
            continue
        deadline_phrase = (
            "ist überfällig"
            if status == ControlCenterStatus.overdue
            else "steht kurzfristig an"
        )
        items.append(
            EnterpriseControlCenterItem(
                section=ControlCenterSection.regulatory_deadlines,
                severity=_due_severity(due_utc, now),
                status=status,
                title=f"Regulatorische Frist: {dl.title}",
                summary_de=f"{dl.category.value.upper()} Frist {deadline_phrase}.",
                due_at=due_utc,
                tenant_id=tenant_id,
                source_type="compliance_deadline",
                source_id=dl.id,
                action_label="Kalender öffnen",
                action_href="/tenant/compliance-overview",
            )
        )

    # AI register/export and board readiness blockers
    systems = ai_repo.list_for_tenant(tenant_id)
    high_risk = [s for s in systems if s.risk_level == "high"]
    for s in high_risk:
        if s.status in {"draft", "inreview"}:
            items.append(
                EnterpriseControlCenterItem(
                    section=ControlCenterSection.register_export_obligations,
                    severity=ControlCenterSeverity.warning,
                    status=ControlCenterStatus.open,
                    title="KI-Register/Export noch nicht belastbar",
                    summary_de=(
                        f"High-Risk-System {s.name} ist noch nicht aktiv und "
                        "sollte vor Export/Board-Reporting finalisiert werden."
                    ),
                    due_at=None,
                    tenant_id=tenant_id,
                    source_type="ai_system",
                    source_id=s.id,
                    action_label="AI-System prüfen",
                    action_href="/tenant/ai-systems",
                )
            )

        if not s.owner_email:
            items.append(
                EnterpriseControlCenterItem(
                    section=ControlCenterSection.board_readiness,
                    severity=ControlCenterSeverity.warning,
                    status=ControlCenterStatus.blocked,
                    title="Board-Readiness: Owner fehlt",
                    summary_de=(
                        f"Für High-Risk-System {s.name} ist kein "
                        "verantwortlicher Owner hinterlegt."
                    ),
                    due_at=None,
                    tenant_id=tenant_id,
                    source_type="ai_system",
                    source_id=s.id,
                    action_label="Owner ergänzen",
                    action_href="/tenant/ai-systems",
                )
            )

    reports = list_ai_compliance_board_reports(session, tenant_id, limit=1)
    if not reports:
        items.append(
            EnterpriseControlCenterItem(
                section=ControlCenterSection.board_readiness,
                severity=ControlCenterSeverity.warning,
                status=ControlCenterStatus.open,
                title="Kein Board-Report vorhanden",
                summary_de="Für den Mandanten wurde noch kein AI-Compliance-Board-Report erstellt.",
                due_at=None,
                tenant_id=tenant_id,
                source_type="board_report",
                source_id="none",
                action_label="Board-Report erzeugen",
                action_href="/board/ai-compliance-report",
            )
        )

    grouped_map: dict[ControlCenterSection, list[EnterpriseControlCenterItem]] = defaultdict(list)
    for it in items:
        grouped_map[it.section].append(it)

    section_labels = {
        ControlCenterSection.audit: "Audit & Nachvollziehbarkeit",
        ControlCenterSection.incidents_reporting: "Incidents & Reporting",
        ControlCenterSection.regulatory_deadlines: "Regulatorische Fristen",
        ControlCenterSection.register_export_obligations: "Register- und Exportpflichten",
        ControlCenterSection.board_readiness: "Board-Readiness",
    }
    grouped_sections = [
        EnterpriseControlCenterSectionGroup(
            section=section,
            label_de=section_labels[section],
            items=sorted(grouped_map.get(section, []), key=lambda x: (x.severity, x.due_at or now)),
        )
        for section in section_labels
    ]

    severity_rank = {
        ControlCenterSeverity.critical: 0,
        ControlCenterSeverity.warning: 1,
        ControlCenterSeverity.info: 2,
    }
    top_urgent = sorted(items, key=lambda x: (severity_rank[x.severity], x.due_at or now))[:8]

    counts = EnterpriseControlCenterSummaryCounts(
        critical=sum(1 for i in items if i.severity == ControlCenterSeverity.critical),
        warning=sum(1 for i in items if i.severity == ControlCenterSeverity.warning),
        info=sum(1 for i in items if i.severity == ControlCenterSeverity.info),
        total_open=len(items),
    )

    markdown = None
    if include_markdown:
        lines = [
            "# Enterprise Control Center (Arbeitsstand)",
            "",
            f"- Mandant: {tenant_id}",
            f"- Kritisch: {counts.critical}",
            f"- Warnung: {counts.warning}",
            f"- Info: {counts.info}",
            f"- Offene Punkte: {counts.total_open}",
            "- Hinweis: Operative Steuerungshilfe, keine Rechtsberatung.",
            "",
            "## Top-urgente Punkte",
        ]
        for i in top_urgent:
            due = i.due_at.isoformat() if i.due_at else "ohne Frist"
            lines.append(f"- [{i.section.value}] {i.title} ({i.severity.value}, {due})")
        markdown = "\n".join(lines).strip() + "\n"

    return EnterpriseControlCenterResponse(
        tenant_id=tenant_id,
        generated_at_utc=now,
        summary_counts=counts,
        grouped_sections=grouped_sections,
        top_urgent_items=top_urgent,
        markdown_de=markdown,
    )
