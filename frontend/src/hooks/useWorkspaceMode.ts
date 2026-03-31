"use client";

import { useMemo } from "react";

import { useWorkspaceTenantMeta } from "@/hooks/useWorkspaceTenantMeta";

export type UseWorkspaceModeResult = ReturnType<typeof useWorkspaceTenantMeta> & {
  /** production | demo | playground (aus API workspace_mode). */
  workspaceMode: "production" | "demo" | "playground";
  modeLabel: string;
  modeHint: string;
  /** Alias zu mutation_blocked für CTAs. */
  mutationsBlocked: boolean;
  /** API-Feld is_demo (Pilot/Seed), unabhängig von workspace_mode. */
  isDemoTenant: boolean;
  /** workspace_mode === "demo". */
  isDemo: boolean;
  isProduction: boolean;
  isPlayground: boolean;
  /** Nur echtes Playground ohne Schreibblock. */
  isPlaygroundWritable: boolean;
  /** Interne Doku (NEXT_PUBLIC_WORKSPACE_MODE_DOCS_URL), sonst leer. */
  docsUrl: string;
};

/**
 * Workspace-UX-Vertrag: leitet Booleans und Texte aus GET /workspace/tenant-meta ab.
 * Zentral nutzen statt verstreuter Demo-Flags.
 */
export function useWorkspaceMode(tenantId: string | null | undefined): UseWorkspaceModeResult {
  const base = useWorkspaceTenantMeta(tenantId);

  return useMemo(() => {
    const wm = base.meta?.workspace_mode ?? "production";
    const docsUrl =
      (typeof process !== "undefined" && process.env.NEXT_PUBLIC_WORKSPACE_MODE_DOCS_URL?.trim()) ||
      "";
    return {
      ...base,
      workspaceMode: wm,
      modeLabel: base.meta?.mode_label ?? "",
      modeHint: base.meta?.mode_hint ?? "",
      mutationsBlocked: base.mutationBlocked,
      isDemoTenant: base.isDemoTenant,
      isDemo: wm === "demo",
      isProduction: wm === "production",
      isPlayground: wm === "playground",
      isPlaygroundWritable: base.isPlaygroundTenant && !base.mutationBlocked,
      docsUrl,
    };
  }, [base]);
}
