import { BoardReportsHubClient } from "@/components/governance/BoardReportsHubClient";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

export default async function TenantBoardReportsPage() {
  const tenantId = await getWorkspaceTenantIdServer();
  return <BoardReportsHubClient tenantId={tenantId} />;
}
