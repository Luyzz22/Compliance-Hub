"use client";

import { WORKSPACE_TENANT_COOKIE } from "@/lib/workspaceTenantConstants";

const MAX_AGE_SEC = 90 * 24 * 60 * 60;

/** Setzt Workspace-Mandant und lädt die Compliance-Übersicht neu (Server liest Cookie). */
export function openWorkspaceTenantAndGoComplianceOverview(tenantId: string): void {
  if (typeof document === "undefined") return;
  const enc = encodeURIComponent(tenantId.trim());
  document.cookie = `${WORKSPACE_TENANT_COOKIE}=${enc}; path=/; max-age=${MAX_AGE_SEC}; SameSite=Lax`;
  window.location.assign("/tenant/compliance-overview");
}
