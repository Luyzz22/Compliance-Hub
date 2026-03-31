"use client";

import { useMemo } from "react";

import { featureAiActEvidenceViews } from "@/lib/config";
import { useWorkspaceTenantMeta } from "@/hooks/useWorkspaceTenantMeta";

export function useAiActEvidenceNav(workspaceTenantId: string) {
  const { meta, loading } = useWorkspaceTenantMeta(workspaceTenantId);
  const envOn = featureAiActEvidenceViews();
  const visible = useMemo(() => {
    if (!envOn || loading || !meta) {
      return false;
    }
    return Boolean(meta.feature_ai_act_evidence_views && meta.can_view_ai_evidence);
  }, [envOn, loading, meta]);

  const href = `/tenants/${encodeURIComponent(workspaceTenantId)}/evidence/ai-act`;

  return { visible, href, loading, meta };
}
