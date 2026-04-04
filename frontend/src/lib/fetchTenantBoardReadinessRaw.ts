import "server-only";

import type {
  RawAIActDocListResponse,
  RawAISystemRow,
  RawAIComplianceOverview,
  RawBoardReportListItem,
  RawComplianceDashboard,
  RawComplianceStatusEntry,
  RawEuAIActReadinessOverview,
  RawTenantAIGovernanceSetup,
  RawTenantSetupStatus,
  TenantBoardReadinessRaw,
} from "@/lib/tenantBoardReadinessRawTypes";

export type {
  RawAIActDocListItem,
  RawAIActDocListResponse,
  RawAIComplianceOverview,
  RawAISystemRow,
  RawBoardReportListItem,
  RawComplianceDashboard,
  RawComplianceStatusEntry,
  RawEuAIActReadinessOverview,
  RawSystemReadiness,
  RawTenantAIGovernanceSetup,
  RawTenantSetupStatus,
  TenantBoardReadinessRaw,
} from "@/lib/tenantBoardReadinessRawTypes";

function apiBase(): string {
  return (
    process.env.COMPLIANCEHUB_API_BASE_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ||
    "http://localhost:8000"
  );
}

function apiKey(): string {
  return (
    process.env.COMPLIANCEHUB_API_KEY?.trim() ||
    process.env.NEXT_PUBLIC_API_KEY?.trim() ||
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

async function getJson<T>(
  tenantId: string,
  path: string,
): Promise<{ ok: boolean; data: T | null; status: number }> {
  const base = apiBase();
  const url = `${base}${path}`;
  try {
    const res = await fetch(url, { headers: tenantHeaders(tenantId), cache: "no-store" });
    if (!res.ok) return { ok: false, data: null, status: res.status };
    const data = (await res.json()) as T;
    return { ok: true, data, status: res.status };
  } catch {
    return { ok: false, data: null, status: 0 };
  }
}

/**
 * Loads tenant-scoped governance artefacts for Board Readiness.
 * Best-effort: partial data still returns `fetch_ok` if any core call succeeded.
 */
export async function fetchTenantBoardReadinessRaw(tenantId: string): Promise<TenantBoardReadinessRaw> {
  const tid = encodeURIComponent(tenantId);
  let fetch_ok = false;

  const systemsRes = await getJson<RawAISystemRow[]>(tenantId, "/api/v1/ai-systems");
  if (systemsRes.ok && Array.isArray(systemsRes.data)) fetch_ok = true;
  const ai_systems = systemsRes.ok && Array.isArray(systemsRes.data) ? systemsRes.data : [];

  const dashRes = await getJson<RawComplianceDashboard>(
    tenantId,
    "/api/v1/compliance/dashboard",
  );
  if (dashRes.ok) fetch_ok = true;
  const compliance_dashboard = dashRes.ok ? dashRes.data : null;

  const euRes = await getJson<RawEuAIActReadinessOverview>(
    tenantId,
    "/api/v1/ai-governance/readiness/eu-ai-act",
  );
  if (euRes.ok) fetch_ok = true;
  const eu_ai_act_readiness = euRes.ok ? euRes.data : null;

  const overviewRes = await getJson<RawAIComplianceOverview>(
    tenantId,
    "/api/v1/ai-governance/compliance/overview",
  );
  if (overviewRes.ok) fetch_ok = true;
  const ai_compliance_overview = overviewRes.ok ? overviewRes.data : null;

  const setupRes = await getJson<RawTenantSetupStatus>(
    tenantId,
    `/api/v1/tenants/${tid}/setup-status`,
  );
  if (setupRes.ok) fetch_ok = true;
  const setup_status = setupRes.ok ? setupRes.data : null;

  const agRes = await getJson<RawTenantAIGovernanceSetup>(
    tenantId,
    `/api/v1/tenants/${tid}/ai-governance-setup`,
  );
  if (agRes.ok) fetch_ok = true;
  const ai_governance_setup = agRes.ok ? agRes.data : null;

  const brRes = await getJson<RawBoardReportListItem[]>(
    tenantId,
    `/api/v1/tenants/${tid}/board/ai-compliance-reports?limit=20`,
  );
  const board_reports = brRes.ok && Array.isArray(brRes.data) ? brRes.data : [];
  if (brRes.ok) fetch_ok = true;

  const highRiskIds = new Set<string>();
  for (const row of compliance_dashboard?.systems ?? []) {
    if (row.risk_level === "high_risk") highRiskIds.add(row.ai_system_id);
  }

  const compliance_by_system: Record<string, RawComplianceStatusEntry[]> = {};
  const ai_act_doc_items_by_system: Record<string, RawAIActDocListItem[]> = {};
  const ai_act_docs_errors: Record<string, boolean> = {};

  for (const sysId of highRiskIds) {
    const sid = encodeURIComponent(sysId);
    const cRes = await getJson<RawComplianceStatusEntry[]>(
      tenantId,
      `/api/v1/ai-systems/${sid}/compliance`,
    );
    if (cRes.ok && Array.isArray(cRes.data)) {
      fetch_ok = true;
      compliance_by_system[sysId] = cRes.data;
    }

    const docRes = await getJson<RawAIActDocListResponse>(
      tenantId,
      `/api/v1/ai-systems/${sid}/ai-act-docs`,
    );
    if (!docRes.ok) {
      ai_act_docs_errors[sysId] = true;
      continue;
    }
    fetch_ok = true;
    ai_act_doc_items_by_system[sysId] = docRes.data?.items ?? [];
  }

  return {
    tenant_id: tenantId,
    fetch_ok,
    ai_systems,
    compliance_by_system,
    ai_act_doc_items_by_system,
    compliance_dashboard,
    eu_ai_act_readiness,
    ai_compliance_overview,
    setup_status,
    ai_governance_setup,
    board_reports,
    ai_act_docs_errors,
  };
}
