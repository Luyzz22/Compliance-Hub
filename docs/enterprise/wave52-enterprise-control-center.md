# Wave 52 – Enterprise Control Center

## Zweck

Der Enterprise Control Center View liefert einen kompakten, operativen Steuerungsblick fuer
Mandanten und Advisor. Er ist kein BI-Dashboard, sondern priorisiert:

- Was ist jetzt kritisch?
- Welche Fristen sind als naechstes faellig?
- Welche Register-/Export-/Board-Readiness-Luecken blockieren Governance-Operationen?

## Modell

Backend-Modell: `app/enterprise_control_center_models.py`

- `EnterpriseControlCenterItem`
  - `section` (audit, incidents_reporting, regulatory_deadlines, register_export_obligations, board_readiness)
  - `severity` (critical, warning, info)
  - `status` (open, due_soon, overdue, blocked, ok)
  - `due_at`, `tenant_id`, `source_type`, `source_id`
  - `action_label`, `action_href`
- `EnterpriseControlCenterResponse`
  - `summary_counts` (critical/warning/info/total_open)
  - `grouped_sections`
  - `top_urgent_items`
  - optional `markdown_de`

## Source-Mapping

Service: `app/services/enterprise_control_center.py`

- Audit/Governance-Ereignisse: `AuditLogRepository`
- NIS2-Incidents + Reporting-Fristen: `NIS2IncidentRepository`
- Compliance-Kalender-Fristen: `ComplianceDeadlineRepository`
- KI-System-Readiness-Signale: `AISystemRepository`
- Board-Readiness-Basis: bestehende Board-Report-Liste (`list_ai_compliance_board_reports`)

Der View nutzt auditable Quellen und explizite, deterministische Heuristiken (keine versteckte LLM-Logik).

## API

- `GET /api/internal/enterprise/control-center`
- Query: `include_markdown=true|false`
- Schutz:
  - tenant-safe ueber `AuthContext`
  - RBAC ueber `require_permission(Permission.VIEW_DASHBOARD)`

## UI-Integration

- Tenant-Page: `frontend/src/app/tenant/control-center/page.tsx`
- Einstieg ueber `Compliance-Übersicht` (`/tenant/compliance-overview`)
- Fokus: Top-urgent, due events, gruppierte Blocker

## Abgrenzung zu SLA/Reminders/Incidents/Calendar

- Incident-Workflow bleibt kanonisch in NIS2.
- Compliance-Calendar bleibt kanonisch fuer regulatorische Faelligkeiten.
- Control Center dupliziert keine Reminder-/SLA-Mechanik; es aggregiert und priorisiert nur.

## Non-Goals / Limitierungen

- Keine neue fachliche Workflow-Engine.
- Kein Ersatz fuer detaillierte Fach-Views (Incidents, Audit-Log, Board-Report-Detail).
- Readiness-Interpretation bleibt governance-operativ und ist keine Rechtsberatung.
