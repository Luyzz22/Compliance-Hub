/**
 * Governance Workflow Orchestration (deterministische Regeln, mandantisoliert).
 */

import type { WorkflowRunListItem, WorkflowRunResponse, WorkflowRunSummary } from "@/lib/governanceWorkflowTypes";

export type { WorkflowRunListItem, WorkflowRunResponse, WorkflowRunSummary } from "@/lib/governanceWorkflowTypes";

function apiBase(): string {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ||
    process.env.COMPLIANCEHUB_API_BASE_URL?.trim() ||
    "http://localhost:8000"
  );
}

function apiKey(): string {
  return (
    process.env.NEXT_PUBLIC_API_KEY?.trim() ||
    process.env.COMPLIANCEHUB_API_KEY?.trim() ||
    "tenant-overview-key"
  );
}

function headers(tenantId: string, extra?: Record<string, string>): Record<string, string> {
  return {
    "x-api-key": apiKey(),
    "x-tenant-id": tenantId,
    "Content-Type": "application/json",
    ...extra,
  };
}

const BASE = "/api/v1/governance/workflows";

export class WorkflowApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail: string = ""
  ) {
    super(message);
    this.name = "WorkflowApiError";
  }
}

export interface GovernanceWorkflowKpisDto {
  open_tasks: number;
  overdue_tasks: number;
  escalated_tasks: number;
  notifications_queued: number;
  workflow_events_24h: number;
}

export interface GovernanceWorkflowDashboardDto {
  kpis: GovernanceWorkflowKpisDto;
  rule_bundle_version: string;
  recent_runs: WorkflowRunListItem[];
  templates: {
    id: string;
    code: string;
    title: string;
    description: string;
    default_sla_days: number;
    is_system: number;
  }[];
}

export async function fetchWorkflowDashboard(
  tenantId: string
): Promise<GovernanceWorkflowDashboardDto> {
  const r = await fetch(`${apiBase()}${BASE}`, { headers: headers(tenantId) });
  if (!r.ok) throw new Error(`Dashboard ${r.status}`);
  return (await r.json()) as GovernanceWorkflowDashboardDto;
}

export async function postWorkflowRun(
  tenantId: string
): Promise<WorkflowRunResponse> {
  const r = await fetch(`${apiBase()}${BASE}/run`, {
    method: "POST",
    headers: headers(tenantId),
    body: JSON.stringify({ rule_profile: "default" }),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new WorkflowApiError(`Run ${r.status}`, r.status, t);
  }
  return (await r.json()) as WorkflowRunResponse;
}

export interface WorkflowTaskListItemDto {
  id: string;
  title: string;
  status: string;
  priority: string;
  source_type: string;
  source_id: string;
  assignee_user_id: string | null;
  due_at_utc: string | null;
  template_code: string | null;
  framework_tags: string[];
  escalation_level: number;
  created_at_utc: string;
  updated_at_utc: string;
  is_overdue: boolean;
}

export async function fetchWorkflowTasks(
  tenantId: string,
  q: {
    status?: string;
    source_type?: string;
    assignee?: string;
    severity?: string;
    framework?: string;
  }
): Promise<WorkflowTaskListItemDto[]> {
  const p = new URLSearchParams();
  if (q.status) p.set("status", q.status);
  if (q.source_type) p.set("source_type", q.source_type);
  if (q.assignee) p.set("assignee", q.assignee);
  if (q.severity) p.set("severity", q.severity);
  if (q.framework) p.set("framework", q.framework);
  const qs = p.toString();
  const r = await fetch(`${apiBase()}${BASE}/tasks${qs ? `?${qs}` : ""}`, {
    headers: headers(tenantId),
  });
  if (!r.ok) throw new Error(`Tasks ${r.status}`);
  return (await r.json()) as WorkflowTaskListItemDto[];
}

export interface WorkflowEventDto {
  id: string;
  at_utc: string;
  event_type: string;
  severity: string;
  ref_task_id: string | null;
  source_type: string;
  source_id: string;
  message: string;
  payload_json: Record<string, unknown>;
}

export async function fetchWorkflowEvents(tenantId: string): Promise<WorkflowEventDto[]> {
  const r = await fetch(`${apiBase()}${BASE}/events?limit=100`, { headers: headers(tenantId) });
  if (!r.ok) throw new Error(`Events ${r.status}`);
  return (await r.json()) as WorkflowEventDto[];
}

export interface WorkflowNotificationDto {
  id: string;
  ref_task_id: string | null;
  channel: string;
  status: string;
  title: string;
  body_text: string;
  created_at_utc: string;
}

export interface WorkflowNotificationDeliveryDto {
  id: string;
  notification_id: string;
  channel: string;
  result: string;
  detail: string | null;
  delivered_at_utc: string;
}

export async function fetchWorkflowNotifications(
  tenantId: string
): Promise<WorkflowNotificationDto[]> {
  const r = await fetch(`${apiBase()}${BASE}/notifications?limit=100`, {
    headers: headers(tenantId),
  });
  if (!r.ok) throw new Error(`Notifications ${r.status}`);
  return (await r.json()) as WorkflowNotificationDto[];
}

export async function fetchNotificationDeliveries(
  tenantId: string
): Promise<WorkflowNotificationDeliveryDto[]> {
  const r = await fetch(`${apiBase()}${BASE}/notification-deliveries?limit=100`, {
    headers: headers(tenantId),
  });
  if (!r.ok) throw new Error(`Deliveries ${r.status}`);
  return (await r.json()) as WorkflowNotificationDeliveryDto[];
}

export interface WorkflowTaskDetailDto {
  id: string;
  title: string;
  description: string | null;
  status: string;
  source_type: string;
  source_id: string;
  source_ref: Record<string, unknown>;
  assignee_user_id: string | null;
  due_at_utc: string | null;
  last_comment: string | null;
  is_overdue: boolean;
  history: {
    at_utc: string;
    from_status: string | null;
    to_status: string;
    actor_id: string;
    note: string | null;
  }[];
}

export async function fetchWorkflowTaskDetail(
  tenantId: string,
  taskId: string
): Promise<WorkflowTaskDetailDto> {
  const r = await fetch(`${apiBase()}${BASE}/tasks/${encodeURIComponent(taskId)}`, {
    headers: headers(tenantId),
  });
  if (!r.ok) throw new Error(`Task ${r.status}`);
  return (await r.json()) as WorkflowTaskDetailDto;
}

function parseErrorDetailFromBody(raw: string): string {
  try {
    const j = JSON.parse(raw) as { detail?: unknown };
    if (typeof j.detail === "string" && j.detail) {
      return j.detail;
    }
  } catch {
    // ignore
  }
  if (raw.length > 0 && raw.length < 500) {
    return raw;
  }
  return "Ungültige Anforderung";
}

export async function patchWorkflowTask(
  tenantId: string,
  taskId: string,
  body: { status?: string; last_comment?: string; assignee_user_id?: string | null }
): Promise<WorkflowTaskListItemDto> {
  const r = await fetch(`${apiBase()}${BASE}/tasks/${encodeURIComponent(taskId)}`, {
    method: "PATCH",
    headers: headers(tenantId),
    body: JSON.stringify(body),
  });
  const text = await r.text();
  if (r.status === 422) {
    const d = parseErrorDetailFromBody(text);
    throw new WorkflowApiError(
      "Ungültiger Task-Status oder Konflikt (422)",
      422,
      d
    );
  }
  if (!r.ok) {
    throw new WorkflowApiError(`PATCH task ${r.status}`, r.status, text);
  }
  return JSON.parse(text) as WorkflowTaskListItemDto;
}

export async function postTestNotification(
  tenantId: string
): Promise<{ notification_id: string; delivery_id: string }> {
  const r = await fetch(`${apiBase()}${BASE}/notifications/test`, {
    method: "POST",
    headers: headers(tenantId),
    body: JSON.stringify({
      channel: "test",
      title: "Test aus Governance-UI",
      body: "MVP: nur Datensatz, kein echter Versand.",
    }),
  });
  if (!r.ok) throw new Error(`Test notification ${r.status}`);
  return (await r.json()) as { notification_id: string; delivery_id: string };
}
