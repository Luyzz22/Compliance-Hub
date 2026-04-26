/**
 * Governance Workflow — clientseitige Domäne (1:1 mit API, app/governance_workflow_service.py:
 * WORKFLOW_TASK_ALLOWED_STATUSES, Source-Typen aus _materialize-Regeln).
 *
 * "blocked" / "deferred" sind hier absichtlich nicht als Task-Status: die API speichert nur
 * open | in_progress | done | cancelled | escalated.
 */

/** Laut API PATCH / ggf. ORM-Validierung (keine freien Strings). */
export const WORKFLOW_TASK_STATUS_VALUES = [
  "open",
  "in_progress",
  "done",
  "cancelled",
  "escalated",
] as const;

export type WorkflowTaskStatus = (typeof WORKFLOW_TASK_STATUS_VALUES)[number];

/**
 * Bekannte source_type-Werte aus dem Backend (Materialisierung pro Quell-Entität).
 * Beim Hinzufügen neuer Quellen: Service + Pydantic + diesen Union erweitern.
 */
export const WORKFLOW_SOURCE_TYPE_VALUES = [
  "remediation_action",
  "governance_control",
  "board_report_action",
  "service_health_incident",
] as const;

export type WorkflowSourceType = (typeof WORKFLOW_SOURCE_TYPE_VALUES)[number];

/** task.priority bzw. Filter "severity" (entspricht Remediation-/Task-Priorität). */
export const WORKFLOW_PRIORITY_VALUES = ["critical", "high", "medium", "low"] as const;

export type WorkflowTaskPriority = (typeof WORKFLOW_PRIORITY_VALUES)[number];

/** Run.summary_json bzw. POST /run-Response-Teilfelder. */
export interface WorkflowRunSummary {
  tasks_materialized?: number;
  /** Anzahl während des Laufs erzeugter governance_workflow_events (Backend: events_written). */
  events_written?: number;
  remediation_overdue?: number;
  service_incidents?: number;
  board_actions?: number;
  evidence_gaps?: number;
  overdue_reviews?: number;
  remediation_notification_events?: number;
}

export interface WorkflowRunListItem {
  id: string;
  tenant_id?: string;
  status: string;
  rule_bundle_version: string;
  summary: WorkflowRunSummary;
  started_at_utc: string;
  completed_at_utc: string | null;
}

export interface WorkflowRunResponse {
  run_id: string;
  status: string;
  tasks_materialized: number;
  events_written: number;
  notifications_queued: number;
  rule_bundle_version: string;
}

export function isWorkflowTaskStatus(s: string): s is WorkflowTaskStatus {
  return (WORKFLOW_TASK_STATUS_VALUES as readonly string[]).includes(s);
}

/** Strikte Prüfung (Client-Guard, vor PATCH). */
export function assertWorkflowTaskStatus(s: string): asserts s is WorkflowTaskStatus {
  if (!isWorkflowTaskStatus(s)) {
    throw new Error(`Ungültiger Task-Status: ${s}`);
  }
}

const TERMINAL: readonly WorkflowTaskStatus[] = ["done", "cancelled"];

/**
 * UI-Regel: von abgeschlossen/storniert kein „Wiedereröffnen“ zum Bearbeiten (MVP).
 * (API-Änderung für bewusstes Re-Open wäre Phase 2.)
 */
export function isAllowedStatusTransition(
  from: string,
  to: WorkflowTaskStatus
): boolean {
  if (from === to) return true;
  if (!isWorkflowTaskStatus(from)) {
    return true;
  }
  if (TERMINAL.includes(from) && from !== to) {
    return false;
  }
  return true;
}

/**
 * Liest events_written aus Run-Summary (Key wie Backend: events_written; alias event_count
 * wird nicht erwartet).
 */
export function getEventsCountFromRunSummary(
  s: WorkflowRunSummary | undefined | null
): number {
  if (!s || typeof s.events_written !== "number" || !Number.isFinite(s.events_written)) {
    return 0;
  }
  return s.events_written;
}
