import { OperationsResilienceWorkspaceClient } from "@/components/governance/OperationsResilienceWorkspaceClient";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function TenantGovernanceOperationsPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  return <OperationsResilienceWorkspaceClient tenantId={tenantId} />;
}
