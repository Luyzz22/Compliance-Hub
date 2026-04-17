import { GovernanceControlsWorkspaceClient } from "@/components/governance/GovernanceControlsWorkspaceClient";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function TenantGovernanceControlsPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  return <GovernanceControlsWorkspaceClient tenantId={tenantId} />;
}
