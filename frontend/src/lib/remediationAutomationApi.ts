export interface RemediationAutomationSummaryDto {
  overdue_actions: number;
  severe_escalations_open: number;
  management_escalations_open: number;
  reminders_due_today: number;
  auto_generated_actions_7d: number;
}

export interface RemediationEscalationItemDto {
  id: string;
  action_id: string;
  severity: string;
  reason_code: string;
  detail: string | null;
  status: string;
  created_at_utc: string;
  run_id: string | null;
}

export interface RemediationReminderItemDto {
  id: string;
  action_id: string;
  kind: string;
  remind_at_utc: string;
  status: string;
  created_at_utc: string;
  run_id: string | null;
}

export interface RemediationAutomationRunResponseDto {
  run_id: string;
  escalations_created: number;
  reminders_upserted: number;
  events_written: number;
  generated_actions: number;
  rule_keys: string[];
}

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

function headers(tenantId: string): Record<string, string> {
  return { "x-api-key": apiKey(), "x-tenant-id": tenantId, "Content-Type": "application/json" };
}

const BASE = "/api/v1/governance/remediation-actions";

export async function fetchAutomationSummary(
  tenantId: string,
): Promise<RemediationAutomationSummaryDto> {
  const base = apiBase().replace(/\/$/, "");
  const res = await fetch(`${base}${BASE}/automation/summary`, {
    headers: headers(tenantId),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Automation summary ${res.status}`);
  return (await res.json()) as RemediationAutomationSummaryDto;
}

export async function postAutomationRun(
  tenantId: string,
): Promise<RemediationAutomationRunResponseDto> {
  const base = apiBase().replace(/\/$/, "");
  const res = await fetch(`${base}${BASE}/automation/run`, {
    method: "POST",
    headers: headers(tenantId),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Automation run ${res.status}`);
  return (await res.json()) as RemediationAutomationRunResponseDto;
}

export async function fetchEscalations(
  tenantId: string,
  params: { status?: string; severity?: string; limit?: number } = {},
): Promise<{ items: RemediationEscalationItemDto[] }> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.severity) qs.set("severity", params.severity);
  if (params.limit != null) qs.set("limit", String(params.limit));
  const q = qs.toString();
  const base = apiBase().replace(/\/$/, "");
  const res = await fetch(`${base}${BASE}/escalations${q ? `?${q}` : ""}`, {
    headers: headers(tenantId),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Escalations ${res.status}`);
  return (await res.json()) as { items: RemediationEscalationItemDto[] };
}

export async function fetchReminders(
  tenantId: string,
  params: { status?: string; limit?: number } = {},
): Promise<{ items: RemediationReminderItemDto[] }> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.limit != null) qs.set("limit", String(params.limit));
  const q = qs.toString();
  const base = apiBase().replace(/\/$/, "");
  const res = await fetch(`${base}${BASE}/reminders${q ? `?${q}` : ""}`, {
    headers: headers(tenantId),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Reminders ${res.status}`);
  return (await res.json()) as { items: RemediationReminderItemDto[] };
}
