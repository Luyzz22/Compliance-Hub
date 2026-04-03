import "server-only";

export type TenantAiGovernanceSetupJson = {
  tenant_id?: string;
  progress_steps?: number[];
  active_frameworks?: string[];
  flags?: Record<string, boolean>;
};

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

export type GtmTenantGovernanceSnapshot = {
  tenant_id: string;
  ai_systems_count: number;
  progress_steps: number[];
  active_frameworks: string[];
  fetch_ok: boolean;
  http_status?: number;
};

/**
 * Liest Governance-Setup und AI-System-Anzahl für einen Mandanten (serverseitig).
 * Fehler → fetch_ok false, Zähler 0.
 */
export async function fetchTenantGovernanceSnapshot(tenantId: string): Promise<GtmTenantGovernanceSnapshot> {
  const base = apiBase();
  const tid = encodeURIComponent(tenantId);
  const h = tenantHeaders(tenantId);

  let progress_steps: number[] = [];
  let active_frameworks: string[] = [];
  let ai_systems_count = 0;
  let fetch_ok = false;
  let http_status: number | undefined;

  try {
    const setupRes = await fetch(`${base}/api/v1/tenants/${tid}/ai-governance-setup`, {
      headers: h,
      cache: "no-store",
    });
    http_status = setupRes.status;
    if (setupRes.ok) {
      const j = (await setupRes.json()) as TenantAiGovernanceSetupJson;
      if (Array.isArray(j.progress_steps)) {
        progress_steps = j.progress_steps.filter((x): x is number => typeof x === "number");
      }
      if (Array.isArray(j.active_frameworks)) {
        active_frameworks = j.active_frameworks.filter((x): x is string => typeof x === "string");
      }
      fetch_ok = true;
    }
  } catch {
    /* try ai-systems below */
  }

  try {
    const sysRes = await fetch(`${base}/api/v1/ai-systems`, {
      headers: h,
      cache: "no-store",
    });
    if (sysRes.ok) {
      const list = (await sysRes.json()) as unknown;
      if (Array.isArray(list)) {
        ai_systems_count = list.length;
      }
      fetch_ok = true;
    }
  } catch {
    /* ignore */
  }

  return {
    tenant_id: tenantId,
    ai_systems_count,
    progress_steps,
    active_frameworks,
    fetch_ok,
    http_status,
  };
}
