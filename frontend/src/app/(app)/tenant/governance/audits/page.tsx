import { AuditsHubClient } from "@/components/governance/AuditsHubClient";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function TenantGovernanceAuditsPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  return <AuditsHubClient tenantId={tenantId} />;
}
