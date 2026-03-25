"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchTenantWorkspaceMeta, type TenantWorkspaceMetaDto } from "@/lib/api";

export type UseWorkspaceTenantMetaResult = {
  meta: TenantWorkspaceMetaDto | null;
  loading: boolean;
  error: string | null;
  /** API lehnt mutierende Requests ab (403 demo_tenant_readonly). */
  mutationBlocked: boolean;
  isDemoTenant: boolean;
  isPlaygroundTenant: boolean;
  refetch: () => void;
};

/**
 * Lädt GET /api/v1/workspace/tenant-meta für Workspace-CTAs (Demo-Badge, Schreibschutz-Hinweise).
 */
export function useWorkspaceTenantMeta(tenantId: string | null | undefined): UseWorkspaceTenantMetaResult {
  const [meta, setMeta] = useState<TenantWorkspaceMetaDto | null>(null);
  const [loading, setLoading] = useState(Boolean(tenantId?.trim()));
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const tid = tenantId?.trim() ?? "";

  useEffect(() => {
    if (!tid) {
      setMeta(null);
      setLoading(false);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    void (async () => {
      try {
        const m = await fetchTenantWorkspaceMeta(tid);
        if (!cancelled) {
          setMeta(m);
        }
      } catch (e) {
        if (!cancelled) {
          setMeta(null);
          setError(e instanceof Error ? e.message : "Workspace-Meta nicht verfügbar");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tid, tick]);

  const refetch = useCallback(() => setTick((n) => n + 1), []);

  return useMemo(
    () => ({
      meta,
      loading,
      error,
      mutationBlocked: Boolean(meta?.mutation_blocked),
      isDemoTenant: Boolean(meta?.is_demo),
      isPlaygroundTenant: Boolean(meta?.demo_playground),
      refetch,
    }),
    [meta, loading, error, refetch],
  );
}
