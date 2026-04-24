import { RemediationAutomationWorkspaceClient } from "@/components/governance/RemediationAutomationWorkspaceClient";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function TenantRemediationAutomationPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  return <RemediationAutomationWorkspaceClient tenantId={tenantId} />;
}
