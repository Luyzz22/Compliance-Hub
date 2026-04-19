/**
 * Audit readiness & evidence completeness — GET /api/v1/governance/audits/*.
 */

export interface GovernanceAuditCaseRow {
  id: string;
  tenant_id: string;
  title: string;
  description: string | null;
  status: string;
  framework_tags: string[];
  control_ids: string[];
  created_at_utc: string;
  updated_at_utc: string;
  created_by: string | null;
}

export interface AuditReadinessSummary {
  audit_case_id: string;
  overall_readiness_pct: number;
  controls_total: number;
  controls_ready: number;
  evidence_gap_count: number;
  overdue_reviews_count: number;
  by_framework: Array<{
    framework_tag: string;
    controls_in_scope: number;
    controls_ready: number;
    evidence_gap_count: number;
    readiness_pct: number;
  }>;
  gaps: Array<{
    control_id: string;
    control_title: string;
    missing_evidence_type_key: string;
    label_hint: string;
    priority: number;
    recommended_action_de: string;
  }>;
}

export interface AuditReadinessControlRow {
  control_id: string;
  title: string;
  framework_tags: string[];
  status: string;
  owner: string | null;
  evidence_completeness_pct: number;
  missing_evidence_types: string[];
  next_review_at: string | null;
  is_ready: boolean;
  review_overdue: boolean;
}

export interface GovernanceAuditTrailRow {
  created_at_utc: string;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  outcome: string | null;
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
  return { "x-api-key": apiKey(), "x-tenant-id": tenantId };
}

function jsonHeaders(tenantId: string): Record<string, string> {
  return { ...tenantHeaders(tenantId), "Content-Type": "application/json" };
}

async function getJson<T>(tenantId: string, path: string): Promise<T> {
  const base = apiBase().replace(/\/$/, "");
  const res = await fetch(`${base}${path}`, { headers: tenantHeaders(tenantId), cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Audits ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function fetchAuditCases(tenantId: string): Promise<GovernanceAuditCaseRow[]> {
  return getJson<GovernanceAuditCaseRow[]>(tenantId, "/api/v1/governance/audits");
}

export async function createAuditCase(
  tenantId: string,
  body: {
    title: string;
    description?: string | null;
    framework_tags: string[];
    control_ids?: string[] | null;
  },
): Promise<GovernanceAuditCaseRow> {
  const base = apiBase().replace(/\/$/, "");
  const res = await fetch(`${base}/api/v1/governance/audits`, {
    method: "POST",
    headers: jsonHeaders(tenantId),
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Create audit ${res.status}`);
  }
  return (await res.json()) as GovernanceAuditCaseRow;
}

export async function fetchAuditReadiness(
  tenantId: string,
  auditId: string,
): Promise<AuditReadinessSummary> {
  return getJson<AuditReadinessSummary>(
    tenantId,
    `/api/v1/governance/audits/${encodeURIComponent(auditId)}/readiness`,
  );
}

export async function fetchAuditControlRows(
  tenantId: string,
  auditId: string,
): Promise<AuditReadinessControlRow[]> {
  return getJson<AuditReadinessControlRow[]>(
    tenantId,
    `/api/v1/governance/audits/${encodeURIComponent(auditId)}/controls`,
  );
}

export async function fetchAuditTrail(
  tenantId: string,
  auditId: string,
): Promise<GovernanceAuditTrailRow[]> {
  return getJson<GovernanceAuditTrailRow[]>(
    tenantId,
    `/api/v1/governance/audits/${encodeURIComponent(auditId)}/trail`,
  );
}
