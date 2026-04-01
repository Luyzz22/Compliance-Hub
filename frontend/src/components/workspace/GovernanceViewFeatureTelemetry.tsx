"use client";

import { useEffect, useRef } from "react";

import { useWorkspaceMode } from "@/hooks/useWorkspaceMode";
import {
  trackWorkspaceFeatureUsed,
  type WorkspaceGovernanceFeatureName,
} from "@/lib/workspaceTelemetry";

export type GovernanceViewFeatureTelemetryProps = {
  tenantId: string;
  featureName: WorkspaceGovernanceFeatureName;
  routeName: string;
  aiSystemId?: string;
  frameworkKey?: string;
};

/**
 * Ein workspace_feature_used pro Seiten-„Leben“ (Strict-Mode-sicher via ref), erst wenn tenant-meta geladen.
 */
export function GovernanceViewFeatureTelemetry({
  tenantId,
  featureName,
  routeName,
  aiSystemId,
  frameworkKey,
}: GovernanceViewFeatureTelemetryProps) {
  const { loading, meta, workspaceMode } = useWorkspaceMode(tenantId);
  const fired = useRef(false);

  useEffect(() => {
    if (loading || !meta || fired.current) {
      return;
    }
    fired.current = true;
    void trackWorkspaceFeatureUsed({
      tenantId,
      workspaceMode,
      featureName,
      routeName,
      aiSystemId,
      frameworkKey,
    });
  }, [loading, meta, tenantId, workspaceMode, featureName, routeName, aiSystemId, frameworkKey]);

  return null;
}
