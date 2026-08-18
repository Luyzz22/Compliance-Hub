import { RemediationWorkspaceClient } from "@/components/governance/RemediationWorkspaceClient";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function TenantRemediationPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  return <RemediationWorkspaceClient tenantId={tenantId} />;
}
