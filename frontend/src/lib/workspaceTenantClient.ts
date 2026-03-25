"use client";

import { WORKSPACE_TENANT_COOKIE } from "@/lib/workspaceTenantConstants";

const MAX_AGE_SEC = 90 * 24 * 60 * 60;

function setWorkspaceTenantCookie(tenantId: string): void {
  if (typeof document === "undefined") return;
  const enc = encodeURIComponent(tenantId.trim());
  document.cookie = `${WORKSPACE_TENANT_COOKIE}=${enc}; path=/; max-age=${MAX_AGE_SEC}; SameSite=Lax`;
}

/** Setzt Workspace-Mandant und navigiert zu einer Tenant-Route (führendes / erforderlich). */
export function openWorkspaceTenantAndGo(tenantId: string, path: string): void {
  if (typeof window === "undefined") return;
  setWorkspaceTenantCookie(tenantId);
  const p = path.startsWith("/") ? path : `/${path}`;
  window.location.assign(p);
}

/** Setzt Workspace-Mandant und lädt die Compliance-Übersicht neu (Server liest Cookie). */
export function openWorkspaceTenantAndGoComplianceOverview(tenantId: string): void {
  openWorkspaceTenantAndGo(tenantId, "/tenant/compliance-overview");
}
