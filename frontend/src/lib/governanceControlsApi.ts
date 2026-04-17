/**
 * Unified Control Layer — API client (GET /api/v1/governance/controls/*).
 * Versioniert wie übrige ComplianceHub-APIs; Auth: NEXT_PUBLIC_* Keys im Browser.
 */

export type ControlStatus =
  | "not_started"
  | "in_progress"
  | "implemented"
  | "needs_review"
  | "overdue";

export type FrameworkFilterTag = "EU_AI_ACT" | "ISO_42001" | "ISO_27001" | "ISO_27701" | "NIS2";

export interface GovernanceControlRow {
  id: string;
  tenant_id: string;
  requirement_id: string | null;
  title: string;
  description: string | null;
  status: string;
  owner: string | null;
  next_review_at: string | null;
  framework_tags: string[];
  source_inputs: Record<string, unknown>;
  created_at_utc: string;
  updated_at_utc: string;
  created_by: string | null;
  framework_mappings: Array<{
    id: string;
    framework: string;
    clause_ref: string;
    mapping_note: string | null;
  }>;
}

export interface ControlsDashboardSummary {
  total_controls: number;
  implemented: number;
  in_progress: number;
  not_started: number;
  needs_review: number;
  overdue_reviews: number;
}

export interface GovernanceControlSuggestion {
  suggestion_key: string;
  title: string;
  description: string;
  framework_tags: string[];
  framework_mappings: Array<{
    framework: string;
    clause_ref: string;
    mapping_note: string | null;
  }>;
  triggered_by: Record<string, unknown>;
}

export interface GovernanceControlEvidenceRow {
  id: string;
  control_id: string;
  title: string;
  body_text: string | null;
  source_type: string;
  source_ref: string | null;
  created_at_utc: string;
  created_by: string | null;
}

export interface GovernanceControlStatusHistoryRow {
  id: string;
  control_id: string;
  from_status: string | null;
  to_status: string;
  changed_at_utc: string;
  changed_by: string | null;
  note: string | null;
}

export interface GovernanceControlsListResult {
  items: GovernanceControlRow[];
  total: number;
  offset: number;
  limit: number;
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
  };
}

function jsonHeaders(tenantId: string): Record<string, string> {
  return { ...tenantHeaders(tenantId), "Content-Type": "application/json" };
}

async function getJson<T>(tenantId: string, path: string): Promise<T> {
  const base = apiBase().replace(/\/$/, "");
  const url = `${base}${path}`;
  const res = await fetch(url, {
    headers: tenantHeaders(tenantId),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Governance Controls ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function fetchControlsDashboardSummary(
  tenantId: string,
): Promise<ControlsDashboardSummary> {
  return getJson<ControlsDashboardSummary>(
    tenantId,
    "/api/v1/governance/controls/dashboard/summary",
  );
}

export async function fetchGovernanceControls(
  tenantId: string,
  options?: {
    frameworkTag?: FrameworkFilterTag | string;
    search?: string;
    offset?: number;
    limit?: number;
  },
): Promise<GovernanceControlsListResult> {
  const q = new URLSearchParams();
  if (options?.frameworkTag) {
    q.set("framework_tag", options.frameworkTag);
  }
  if (options?.search?.trim()) {
    q.set("search", options.search.trim());
  }
  if (options?.offset != null) {
    q.set("offset", String(options.offset));
  }
  if (options?.limit != null) {
    q.set("limit", String(options.limit));
  }
  const suffix = q.toString() ? `?${q.toString()}` : "";
  const base = apiBase().replace(/\/$/, "");
  const url = `${base}/api/v1/governance/controls${suffix}`;
  const res = await fetch(url, {
    headers: tenantHeaders(tenantId),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Governance Controls ${res.status}`);
  }
  const items = (await res.json()) as GovernanceControlRow[];
  const total = Number(res.headers.get("X-Total-Count") ?? items.length);
  const offset = Number(res.headers.get("X-Page-Offset") ?? options?.offset ?? 0);
  const limit = Number(res.headers.get("X-Page-Limit") ?? options?.limit ?? 200);
  return { items, total, offset, limit };
}

export async function fetchControlSuggestions(
  tenantId: string,
): Promise<GovernanceControlSuggestion[]> {
  return getJson<GovernanceControlSuggestion[]>(tenantId, "/api/v1/governance/controls/suggestions");
}

export async function postMaterializeSuggestion(
  tenantId: string,
  suggestionKey: string,
): Promise<GovernanceControlRow> {
  const base = apiBase().replace(/\/$/, "");
  const url = `${base}/api/v1/governance/controls/from-suggestion`;
  const res = await fetch(url, {
    method: "POST",
    headers: jsonHeaders(tenantId),
    body: JSON.stringify({ suggestion_key: suggestionKey }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Materialize ${res.status}`);
  }
  return (await res.json()) as GovernanceControlRow;
}

export async function fetchControlEvidence(
  tenantId: string,
  controlId: string,
): Promise<GovernanceControlEvidenceRow[]> {
  return getJson<GovernanceControlEvidenceRow[]>(
    tenantId,
    `/api/v1/governance/controls/${encodeURIComponent(controlId)}/evidence`,
  );
}

export async function fetchControlStatusHistory(
  tenantId: string,
  controlId: string,
): Promise<GovernanceControlStatusHistoryRow[]> {
  return getJson<GovernanceControlStatusHistoryRow[]>(
    tenantId,
    `/api/v1/governance/controls/${encodeURIComponent(controlId)}/status-history`,
  );
}

export async function postControlEvidence(
  tenantId: string,
  controlId: string,
  body: {
    title: string;
    body_text?: string | null;
    source_type?: string;
    source_ref?: string | null;
  },
): Promise<GovernanceControlEvidenceRow> {
  const base = apiBase().replace(/\/$/, "");
  const url = `${base}/api/v1/governance/controls/${encodeURIComponent(controlId)}/evidence`;
  const res = await fetch(url, {
    method: "POST",
    headers: jsonHeaders(tenantId),
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Evidence ${res.status}`);
  }
  return (await res.json()) as GovernanceControlEvidenceRow;
}

export async function downloadControlsCsv(tenantId: string): Promise<void> {
  const base = apiBase().replace(/\/$/, "");
  const url = `${base}/api/v1/governance/controls/export`;
  const res = await fetch(url, {
    headers: tenantHeaders(tenantId),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Export ${res.status}`);
  }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "governance_controls_export.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}
