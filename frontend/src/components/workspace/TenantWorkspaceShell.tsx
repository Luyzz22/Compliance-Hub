"use client";

import React from "react";

import { WorkspaceShellModeBannerView } from "@/components/demo/WorkspaceShellModeBanner";
import { useWorkspaceMode } from "@/hooks/useWorkspaceMode";

type Props = {
  tenantId: string;
  children: React.ReactNode;
};

/**
 * Lädt Workspace-Meta einmal für Shell + Banner (Board- und Tenant-Layouts).
 */
export function TenantWorkspaceShell({ tenantId, children }: Props) {
  const { loading, workspaceMode, modeLabel, modeHint, docsUrl } = useWorkspaceMode(tenantId);

  return (
    <>
      <WorkspaceShellModeBannerView
        loading={loading}
        workspaceMode={workspaceMode}
        modeLabel={modeLabel}
        modeHint={modeHint}
        docsUrl={docsUrl}
      />
      {children}
    </>
  );
}
