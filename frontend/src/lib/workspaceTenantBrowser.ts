"use client";

import { WORKSPACE_TENANT_COOKIE } from "@/lib/workspaceTenantConstants";

import { TENANT_ID } from "./api";

/** Liest den aktiven Workspace-Mandanten aus dem Browser-Cookie (Client-only). */
export function readWorkspaceTenantIdFromDocumentCookie(fallback: string = TENANT_ID): string {
  if (typeof document === "undefined") {
    return fallback;
  }
  const name = `${WORKSPACE_TENANT_COOKIE}=`;
  const parts = document.cookie.split("; ");
  for (const p of parts) {
    if (p.startsWith(name)) {
      const raw = p.slice(name.length);
      try {
        return decodeURIComponent(raw);
      } catch {
        return raw;
      }
    }
  }
  return fallback;
}
