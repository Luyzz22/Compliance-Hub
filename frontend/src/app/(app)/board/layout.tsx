import React from "react";

import { TenantWorkspaceShell } from "@/components/workspace/TenantWorkspaceShell";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function BoardLayout({ children }: { children: React.ReactNode }) {
  const tenantId = await getWorkspaceTenantIdServer();
  return <TenantWorkspaceShell tenantId={tenantId}>{children}</TenantWorkspaceShell>;
}
