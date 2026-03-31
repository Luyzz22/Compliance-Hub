import { cookies } from "next/headers";

import { featureDemoMode } from "@/lib/config";
import { DEMO_MODE_SESSION_COOKIE } from "@/lib/workspaceTenantConstants";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.COMPLIANCEHUB_API_BASE_URL ||
  "http://localhost:8000";
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY ||
  process.env.COMPLIANCEHUB_API_KEY ||
  "tenant-overview-key";

export type TenantWorkspaceMeta = {
  tenant_id: string;
  display_name: string;
  is_demo: boolean;
  demo_playground: boolean;
  mutation_blocked: boolean;
  workspace_mode: "production" | "demo" | "playground";
  mode_label: string;
  mode_hint: string;
  demo_mode_feature_enabled: boolean;
};

export async function fetchTenantWorkspaceMetaServer(
  tenantId: string,
): Promise<TenantWorkspaceMeta | null> {
  const url = `${API_BASE_URL}/api/v1/workspace/tenant-meta`;
  const res = await fetch(url, {
    headers: {
      "x-api-key": API_KEY,
      "x-tenant-id": tenantId.trim(),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    return null;
  }
  return (await res.json()) as TenantWorkspaceMeta;
}

export async function isDemoUiDesiredForTenant(tenantId: string): Promise<boolean> {
  if (!featureDemoMode()) {
    return false;
  }
  const jar = await cookies();
  if (jar.get(DEMO_MODE_SESSION_COOKIE)?.value === "1") {
    return true;
  }
  const meta = await fetchTenantWorkspaceMetaServer(tenantId).catch(() => null);
  return Boolean(meta?.is_demo);
}
