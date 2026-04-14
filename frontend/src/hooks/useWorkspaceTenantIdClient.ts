"use client";

import { TENANT_ID } from "@/lib/api";
import { readWorkspaceTenantIdFromDocumentCookie } from "@/lib/workspaceTenantBrowser";

/** Mandanten-ID aus Cookie im Browser, sonst Fallback aus Env (ohne Effect, kein SSR-Mismatch-Risiko bei rein clientseitiger Nutzung). */
export function useWorkspaceTenantIdClient(): string {
  return typeof window === "undefined"
    ? TENANT_ID
    : readWorkspaceTenantIdFromDocumentCookie(TENANT_ID);
}
