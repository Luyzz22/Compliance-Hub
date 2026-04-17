/**
 * Operational Resilience / Service Health (tenant governance).
 *
 * Client-seitig: NEXT_PUBLIC_API_BASE_URL + NEXT_PUBLIC_API_KEY (wie andere Tenant-Boards).
 * Server-only Secrets (COMPLIANCEHUB_*) greifen im Browser nicht — ggf. BFF-Route nachziehen.
 *
 * APIs:
 * - GET /api/v1/governance/operations/kpis
 * - GET /api/v1/governance/operations/health/snapshots?limit=
 * - GET /api/v1/governance/operations/incidents?open_only=
 * - PATCH /api/v1/governance/operations/incidents/{id}/resolve
 *
 * Cron: POST /api/internal/health/poll/run + X-HEALTH-KEY
 */

export interface OperationsKpis {
  last_checked_at: string | null;
  open_incidents: number;
  degraded_services: number;
  down_services: number;
}

export interface ServiceHealthSnapshotRow {
  id: string;
  tenant_id: string;
  poll_run_id: string;
  source: string;
  service_name: string;
  status: "up" | "degraded" | "down";
  checked_at: string;
}

export interface ServiceHealthIncidentRow {
  id: string;
  tenant_id: string;
  service_name: string;
  previous_status: string | null;
  current_status: string;
  severity: "warning" | "critical" | string;
  incident_state: "open" | "resolved" | string;
  source: string;
  detected_at: string;
  resolved_at: string | null;
  title: string;
  summary: string;
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

function tenantHeaders(tenantId: string): Record<string, string> {
  return {
    "x-api-key": apiKey(),
    "x-tenant-id": tenantId,
    "Content-Type": "application/json",
  };
}

function asHealthStatus(raw: string): ServiceHealthSnapshotRow["status"] {
  if (raw === "up" || raw === "degraded" || raw === "down") {
    return raw;
  }
  return "degraded";
}

async function getJson<T>(tenantId: string, path: string): Promise<T> {
  const base = apiBase().replace(/\/$/, "");
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, { headers: tenantHeaders(tenantId), cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Governance Operations API ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

/** KPI-Kacheln (letzte Prüfung, offene Incidents, degraded/down Zähler). */
export async function fetchOperationsKpis(tenantId: string): Promise<OperationsKpis> {
  const raw = await getJson<OperationsKpis>(tenantId, "/api/v1/governance/operations/kpis");
  return {
    last_checked_at:
      raw.last_checked_at === undefined || raw.last_checked_at === null
        ? null
        : String(raw.last_checked_at),
    open_incidents: Number(raw.open_incidents ?? 0),
    degraded_services: Number(raw.degraded_services ?? 0),
    down_services: Number(raw.down_services ?? 0),
  };
}

export async function fetchServiceHealthSnapshots(
  tenantId: string,
  limit = 100,
): Promise<ServiceHealthSnapshotRow[]> {
  const rows = await getJson<unknown[]>(
    tenantId,
    `/api/v1/governance/operations/health/snapshots?limit=${encodeURIComponent(String(limit))}`,
  );
  if (!Array.isArray(rows)) {
    return [];
  }
  return rows.map((r) => {
    const o = r as Record<string, unknown>;
    return {
      id: String(o.id ?? ""),
      tenant_id: String(o.tenant_id ?? ""),
      poll_run_id: String(o.poll_run_id ?? ""),
      source: String(o.source ?? ""),
      service_name: String(o.service_name ?? ""),
      status: asHealthStatus(String(o.status ?? "degraded")),
      checked_at: String(o.checked_at ?? ""),
    };
  });
}

export async function fetchServiceHealthIncidents(
  tenantId: string,
  options?: { open_only?: boolean; limit?: number },
): Promise<ServiceHealthIncidentRow[]> {
  const openOnly = options?.open_only ?? false;
  const limit = options?.limit ?? 100;
  const q = new URLSearchParams({
    open_only: openOnly ? "true" : "false",
    limit: String(limit),
  });
  const rows = await getJson<unknown[]>(
    tenantId,
    `/api/v1/governance/operations/incidents?${q.toString()}`,
  );
  if (!Array.isArray(rows)) {
    return [];
  }
  return rows.map((r) => {
    const o = r as Record<string, unknown>;
    return {
      id: String(o.id ?? ""),
      tenant_id: String(o.tenant_id ?? ""),
      service_name: String(o.service_name ?? ""),
      previous_status: o.previous_status == null ? null : String(o.previous_status),
      current_status: String(o.current_status ?? ""),
      severity: String(o.severity ?? ""),
      incident_state: String(o.incident_state ?? ""),
      source: String(o.source ?? ""),
      detected_at: String(o.detected_at ?? ""),
      resolved_at: o.resolved_at == null ? null : String(o.resolved_at),
      title: String(o.title ?? ""),
      summary: String(o.summary ?? ""),
    };
  });
}

export interface ResolveIncidentResponse {
  id: string;
  incident_state: string;
  resolved_at: string;
}

export async function resolveServiceHealthIncident(
  tenantId: string,
  incidentId: string,
  body?: { resolved_note?: string | null },
): Promise<ResolveIncidentResponse> {
  const base = apiBase().replace(/\/$/, "");
  const url = `${base}/api/v1/governance/operations/incidents/${encodeURIComponent(incidentId)}/resolve`;
  const res = await fetch(url, {
    method: "PATCH",
    headers: tenantHeaders(tenantId),
    cache: "no-store",
    body: JSON.stringify(body ?? {}),
  });
  if (!res.ok) {
    throw new Error(`Resolve incident ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as ResolveIncidentResponse;
}
