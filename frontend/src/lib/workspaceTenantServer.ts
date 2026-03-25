import { cookies } from "next/headers";

import { WORKSPACE_TENANT_COOKIE } from "@/lib/workspaceTenantConstants";

const FALLBACK_TENANT =
  process.env.NEXT_PUBLIC_TENANT_ID ||
  process.env.COMPLIANCEHUB_TENANT_ID ||
  "tenant-overview-001";

export async function getWorkspaceTenantIdServer(): Promise<string> {
  const jar = await cookies();
  const raw = jar.get(WORKSPACE_TENANT_COOKIE)?.value;
  if (raw && raw.trim()) {
    try {
      return decodeURIComponent(raw.trim());
    } catch {
      return raw.trim();
    }
  }
  return FALLBACK_TENANT;
}
