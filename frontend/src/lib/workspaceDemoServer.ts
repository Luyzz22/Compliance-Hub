import { cookies } from "next/headers";

import { featureDemoMode } from "@/lib/config";
import { serverSessionApiFetch } from "@/lib/serverBackendApi";
import { DEMO_MODE_SESSION_COOKIE } from "@/lib/workspaceTenantConstants";

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
  const expectedTenant = tenantId.trim();
  if (!expectedTenant) return null;
  const res = await serverSessionApiFetch("/api/v1/workspace/tenant-meta");
  if (!res.ok) {
    return null;
  }
  const meta = (await res.json()) as TenantWorkspaceMeta;
  return meta.tenant_id === expectedTenant ? meta : null;
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
