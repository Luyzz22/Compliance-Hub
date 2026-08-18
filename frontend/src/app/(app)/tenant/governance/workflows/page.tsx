import { GovernanceWorkflowsWorkspaceClient } from "@/components/governance/GovernanceWorkflowsWorkspaceClient";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function TenantGovernanceWorkflowsPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  return <GovernanceWorkflowsWorkspaceClient tenantId={tenantId} />;
}
