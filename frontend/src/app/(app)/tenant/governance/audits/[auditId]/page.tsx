import { AuditReadinessWorkspaceClient } from "@/components/governance/AuditReadinessWorkspaceClient";
import { getWorkspaceTenantIdServer } from "@/lib/workspaceTenantServer";

interface Props {
  params: Promise<{ auditId: string }>;
}

export default async function TenantGovernanceAuditDetailPage({ params }: Props) {
  const { auditId } = await params;
  const tenantId = await getWorkspaceTenantIdServer();
  return <AuditReadinessWorkspaceClient tenantId={tenantId} auditId={auditId} />;
}
